import math
import numpy as np
from .. import utils
from ..bin import pyluxcore
from .image import ImageExporter
from time import time
from ..utils.errorlog import LuxCoreErrorLog

def find_psys_modifier(obj, psys):
    for mod in obj.modifiers:
        if mod.type == "PARTICLE_SYSTEM" and mod.particle_system.name == psys.name:
            return mod
    return None

def convert_uvs(obj, psys, settings, uv_textures, engine, strands_count, start, dupli_count, mod, num_children):
    failure = np.empty(shape=0, dtype=np.float32)

    if settings.use_active_uv_map or settings.uv_map_name not in obj.data.uv_layers:
        active_uv = utils.find_active_uv(uv_textures)
        if active_uv:
            uv_index = uv_textures.find(active_uv.name)
        else:
            uv_index = -1
    else:
        uv_index = uv_textures.find(settings.uv_map_name)

    if uv_index == -1 or not uv_textures[uv_index].data:
        return failure

    if engine:
        engine.update_stats("Exporting...", "[%s: %s] Preparing %d UV coordinates"
                             % (obj.name, psys.name, strands_count))

    first_particle = psys.particles[0]
    f = psys.uv_on_emitter
    uvs = np.fromiter((elem
                       for i in range(start, dupli_count)
                       for elem in f(mod, particle=psys.particles[i] if num_children == 0 else first_particle,
                                     particle_no=i, uv_no=uv_index)),
                      dtype=np.float32,
                      count=(dupli_count - start) * 2)
    return uvs

def convert_colors(obj, psys, settings, vertex_colors, engine, strands_count, start, dupli_count, mod, num_children):
    failure = np.empty(shape=0, dtype=np.float32)

    if settings.use_active_vertex_color_layer or settings.vertex_color_layer_name not in vertex_colors:
        active_vertex_color_layer = utils.find_active_vertex_color_layer(vertex_colors)
        if active_vertex_color_layer:
            vertex_color_index = vertex_colors.find(active_vertex_color_layer.name)
        else:
            vertex_color_index = -1
    else:
        vertex_color_index = vertex_colors.find(settings.vertex_color_layer_name)

    if vertex_color_index == -1 or not vertex_colors[vertex_color_index].data:
        return failure

    if engine:
        engine.update_stats("Exporting...", "[%s: %s] Preparing %d vertex colors"
                            % (obj.name, psys.name, strands_count))

    first_particle = psys.particles[0]
    f = psys.mcol_on_emitter
    colors = np.fromiter((elem
                          for i in range(start, dupli_count)
                          for elem in f(mod, psys.particles[i] if num_children == 0 else first_particle,
                                        particle_no= i, vcol_no=vertex_color_index)),
                         dtype=np.float32,
                         count=(dupli_count - start) * 3)
    return colors

def get_material(obj, material_index, exporter, depsgraph, is_viewport_render):
    from ..utils import node as utils_node
    from . import material
    if material_index < len(obj.material_slots):
        mat = obj.material_slots[material_index].material

        if mat is None:
            # Note: material.convert returns the fallback material in this case
            msg = "No material attached to slot %d" % (material_index + 1)
            LuxCoreErrorLog.add_warning(msg, obj_name=obj.name)
    else:
        # The object has no material slots
        LuxCoreErrorLog.add_warning("No material defined", obj_name=obj.name)
        # Use fallback material
        mat = None

    if mat:
        if mat.luxcore.node_tree:
            imagemaps = utils_node.find_nodes(mat.luxcore.node_tree, "LuxCoreNodeTexImagemap")
            if imagemaps and not utils_node.has_valid_uv_map(obj):
                msg = (utils.pluralize("%d image texture", len(imagemaps)) + " used, but no UVs defined. "
                       "In case of bumpmaps this can lead to artifacts")
                LuxCoreErrorLog.add_warning(msg, obj_name=obj.name)

        return material.convert(exporter, depsgraph, mat, is_viewport_render, obj.name)
    else:
        return material.fallback()

def convert_hair(exporter, obj, psys, depsgraph, luxcore_scene, is_viewport_render, engine=None):
    try:
        assert psys.settings.render_type == "PATH"
        scene = depsgraph.scene_eval
        start_time = time()

        mod = find_psys_modifier(obj, psys)
        # TODO 2.8 Do we have to check if emitter is on a visible layer
        # if not is_psys_visible(obj, mod, scene, context):
        #    return

        msg = "[%s: %s] Exporting hair" % (obj.name, psys.name)
        print(msg)
        if engine:
            engine.update_stats('Exporting...', msg)

        worldscale = utils.get_worldscale(scene, as_scalematrix=False)

        settings = psys.settings.luxcore.hair
        strand_diameter = settings.hair_size * worldscale
        root_width = settings.root_width / 100
        tip_width = settings.tip_width / 100
        width_offset = settings.width_offset / 100

        if not is_viewport_render:
            steps = 2 ** psys.settings.render_step
        else:
            steps = 2 ** psys.settings.display_step
        points_per_strand = steps + 1

        num_parents = len(psys.particles)
        num_children = len(psys.child_particles)
        dupli_count = num_parents + num_children

        if num_children == 0:
            start = 0
        else:
            # Number of virtual parents reduces the number of exported children
            num_virtual_parents = math.trunc(0.3 * psys.settings.virtual_parents
                                             * psys.settings.child_nbr * num_parents)
            start = num_parents + num_virtual_parents

        # Collect point/color/uv information from Blender
        # (unfortunately this can't be accelerated in C++)
        collection_start = time()
        strands_count = dupli_count - start

        # Point coordinates as a flattened numpy array
        point_count = strands_count * points_per_strand
        if engine:
            engine.update_stats("Exporting...", "[%s: %s] Preparing %d points"
                                % (obj.name, psys.name, point_count))
        co_hair = psys.co_hair
        points = np.fromiter((elem
                              for pindex in range(start, dupli_count)
                              for step in range(points_per_strand)
                              for elem in co_hair(object=obj, particle_no=pindex, step=step)),
                             dtype=np.float32,
                             count=point_count * 3)

        colors = np.empty(shape=0, dtype=np.float32)
        uvs = np.empty(shape=0, dtype=np.float32)
        image_filename = ""
        uvs_needed = settings.copy_uv_coords
        copy_uvs = settings.copy_uv_coords

        if settings.export_color != "none" or uvs_needed:
            emitter_mesh = obj.to_mesh(depsgraph=depsgraph)
            uv_textures = emitter_mesh.uv_layers
            vertex_colors = emitter_mesh.vertex_colors

            if settings.export_color == "uv_texture_map" and settings.image:
                try:
                    image_filename = ImageExporter.export(settings.image, settings.image_user, scene)
                    uvs_needed = True
                except OSError as error:
                    msg = "%s (Object: %s, Particle System: %s)" % (error, obj.name, psys.name)
                    LuxCoreErrorLog.add_warning(msg, obj_name=obj.name)
            elif settings.export_color == "vertex_color":
                colors = convert_colors(obj, psys, settings, vertex_colors, engine,
                                        strands_count, start, dupli_count, mod, num_children)

            if uvs_needed:
                uvs = convert_uvs(obj, psys, settings, uv_textures, engine,
                                  strands_count, start, dupli_count, mod, num_children)

            obj.to_mesh_clear()

        if len(uvs) == 0:
            copy_uvs = False

        print("Collecting Blender hair information took %.3f s" % (time() - collection_start))
        if engine and engine.test_break():
            return

        luxcore_shape_name = utils.get_luxcore_name(obj, is_viewport_render) + "_" + utils.make_key_from_bpy_struct(
            psys)

        if engine:
            engine.update_stats("Exporting...", "Refining Hair System %s" % psys.name)
        success = luxcore_scene.DefineBlenderStrands(luxcore_shape_name, points_per_strand,
                                                     points, colors, uvs, image_filename, settings.gamma,
                                                     copy_uvs, worldscale, strand_diameter,
                                                     root_width, tip_width, width_offset,
                                                     settings.tesseltype, settings.adaptive_maxdepth,
                                                     settings.adaptive_error, settings.solid_sidecount,
                                                     settings.solid_capbottom, settings.solid_captop,
                                                     list(settings.root_color), list(settings.tip_color))

        # Sometimes no hair shape could be created, e.g. if the length
        # of all hairs is 0 (can happen e.g. during animations or if hair length is textured)
        if success:
            # For some reason this index is not starting at 0 but at 1 (Blender is strange)
            lux_mat_name, mat_props = get_material(obj, psys.settings.material - 1, exporter, depsgraph,
                                                   is_viewport_render)

            strandsProps = pyluxcore.Properties()
            strandsProps.Set(mat_props)
            prefix = "scene.objects." + luxcore_shape_name + "."

            strandsProps.Set(pyluxcore.Property(prefix + "material", lux_mat_name))
            strandsProps.Set(pyluxcore.Property(prefix + "shape", luxcore_shape_name))
            if settings.instancing == "enabled":
                # We don't actually need to transform anything, just set an identity matrix so the mesh is instanced
                from mathutils import Matrix
                transform = utils.matrix_to_list(Matrix.Identity(4))
                strandsProps.Set(pyluxcore.Property(prefix + "transformation", transform))

            # TODO 2.8 Adapt visibility checkt to new API
            # visible_to_cam = utils.is_obj_visible_to_cam(obj, scene, is_viewport_render)
            # strandsProps.Set(pyluxcore.Property(prefix + "camerainvisible", not visible_to_cam))

            luxcore_scene.Parse(strandsProps)

        time_elapsed = time() - start_time
        print("[%s: %s] Hair export finished (%.3f s)" % (obj.name, psys.name, time_elapsed))
    except Exception as error:
        msg = "[%s: %s] %s" % (obj.name, psys.name, error)
        LuxCoreErrorLog.add_warning(msg, obj_name=obj.name)
        import traceback
        traceback.print_exc()
