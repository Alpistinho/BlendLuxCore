import bpy
from ... import utils
from ...bin import pyluxcore
from .. import mesh_converter
from ..hair import convert_hair
from .exported_data import ExportedObject
from .. import light
from array import array

MESH_OBJECTS = {"MESH", "CURVE", "SURFACE", "META", "FONT"}
EXPORTABLE_OBJECTS = MESH_OBJECTS | {"LIGHT"}


def get_material(obj, material_index, exporter, depsgraph, is_viewport_render):
    from ...utils.errorlog import LuxCoreErrorLog
    from ...utils import node as utils_node
    from .. import material
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
        use_pointiness = False
        if mat.luxcore.node_tree:
            # Check if a pointiness node exists, better check would be if the node is linked
            use_pointiness = len(utils_node.find_nodes(mat.luxcore.node_tree, "LuxCoreNodeTexPointiness")) > 0
            imagemaps = utils_node.find_nodes(mat.luxcore.node_tree, "LuxCoreNodeTexImagemap")
            if imagemaps and not utils_node.has_valid_uv_map(obj):
                msg = (utils.pluralize("%d image texture", len(imagemaps)) + " used, but no UVs defined. "
                       "In case of bumpmaps this can lead to artifacts")
                LuxCoreErrorLog.add_warning(msg, obj_name=obj.name)

        lux_mat_name, mat_props = material.convert(exporter, depsgraph, mat, is_viewport_render, obj.name)
        return lux_mat_name, mat_props, use_pointiness
    else:
        lux_mat_name, mat_props = material.fallback()
        return lux_mat_name, mat_props, False


class Duplis:
    def __init__(self, exported_obj, matrix, object_id):
        self.exported_obj = exported_obj
        self.matrices = matrix
        self.object_ids = [object_id]

    def add(self, matrix, object_id):
        self.matrices += matrix
        self.object_ids.append(object_id)

    def get_count(self):
        return len(self.object_ids)


class ObjectCache2:
    def __init__(self):
        self.exported_objects = {}
        self.exported_meshes = {}

    def first_run(self, exporter, depsgraph, view_layer, engine, luxcore_scene, scene_props, is_viewport_render):
        # TODO cleanup, support object_ids in DuplicateObject()
        instances = {}
        dupli_props = pyluxcore.Properties()

        for dg_obj_instance in depsgraph.object_instances:
            if dg_obj_instance.is_instance:
                obj = dg_obj_instance.instance_object
                transformation = utils.matrix_to_list(dg_obj_instance.matrix_world)
                object_id = 0

                try:
                    instances[obj].add(transformation, object_id)
                except KeyError:
                    # Fresh export (TODO check first if mesh already exported)
                    use_instancing = True
                    mesh_key = self._get_mesh_key(obj, use_instancing, is_viewport_render)
                    transform = None
                    exported_mesh = mesh_converter.convert(obj, mesh_key, depsgraph, luxcore_scene,
                                                           is_viewport_render, use_instancing, transform)
                    self.exported_meshes[mesh_key] = exported_mesh

                    # Create object
                    exported_obj = None
                    if exported_mesh:
                        mat_names = []
                        for idx, (shape_name, mat_index) in enumerate(exported_mesh.mesh_definitions):
                            lux_mat_name, mat_props, use_pointiness = get_material(obj, mat_index, exporter, depsgraph,
                                                                                   is_viewport_render)
                            dupli_props.Set(mat_props)
                            mat_names.append(lux_mat_name)

                            if use_pointiness:
                                # Replace shape definition with pointiness shape
                                pointiness_shape = shape_name + "_pointiness"
                                prefix = "scene.shapes." + pointiness_shape + "."
                                dupli_props.Set(pyluxcore.Property(prefix + "type", "pointiness"))
                                dupli_props.Set(pyluxcore.Property(prefix + "source", shape_name))
                                exported_mesh.mesh_definitions[idx] = [pointiness_shape, mat_index]

                        if obj.luxcore.id == -1:
                            obj_id = utils.make_object_id(dg_obj_instance)
                        else:
                            obj_id = obj.luxcore.id

                        obj_key = utils.make_key_from_instance(dg_obj_instance)
                        # TODO use identity matrix for transform instead of None?
                        exported_obj = ExportedObject(obj_key, exported_mesh.mesh_definitions, mat_names,
                                                      transform, obj.luxcore.visible_to_camera, obj_id)
                        dupli_props.Set(exported_obj.get_props())

                    # What I really wanted to do
                    instances[obj] = Duplis(exported_obj, transformation, object_id)
            else:
                obj = dg_obj_instance.object
                if not (self._is_visible(dg_obj_instance, obj) or obj.visible_get(view_layer=view_layer)):
                    continue

                self._convert_obj(exporter, dg_obj_instance, obj, depsgraph,
                                  luxcore_scene, scene_props, is_viewport_render)
                if engine:
                    # Objects are the most expensive to export, so they dictate the progress
                    # engine.update_progress(index / obj_amount)
                    if engine.test_break():
                        return False

        # Need to parse so we have the dupli objects available for DuplicateObject
        luxcore_scene.Parse(dupli_props)

        for obj, duplis in instances.items():
            print("obj", obj.name, "has", duplis.get_count(), "instances")

            for part in duplis.exported_obj.parts:
                src_name = part.lux_obj
                dst_name = src_name + "dupli"
                transformations = array("f", duplis.matrices)
                object_ids = array("I", duplis.object_ids)
                luxcore_scene.DuplicateObject(src_name, dst_name, duplis.get_count(), transformations, object_ids)

                # TODO: support steps and times (motion blur)
                # steps = 0 # TODO
                # times = array("f", [])
                # luxcore_scene.DuplicateObject(src_name, dst_name, count, steps, times, transformations)

                # Delete the object we used for duplication, we don't want it to show up in the scene
                luxcore_scene.DeleteObject(src_name)

        self._debug_info()
        return True

    def _debug_info(self):
        print("Objects in cache:", len(self.exported_objects))
        print("Meshes in cache:", len(self.exported_meshes))
        # for key, exported_mesh in self.exported_meshes.items():
        #     if exported_mesh:
        #         print(key, exported_mesh.mesh_definitions)
        #     else:
        #         print(key, "mesh is None")

    def _is_visible(self, dg_obj_instance, obj):
        # TODO if this code needs to be used elsewhere (e.g. in material preview),
        #  move it to utils (it doesn't concern this cache class)
        return dg_obj_instance.show_self and obj.type in EXPORTABLE_OBJECTS

    def _get_mesh_key(self, obj, use_instancing, is_viewport_render=True):
        # Important: we need the data of the original object, not the evaluated one.
        # The instancing state has to be part of the key because a non-instanced mesh
        # has its transformation baked-in and can't be used by other instances.
        modified = utils.has_deforming_modifiers(obj.original)
        source = obj.original.data if (use_instancing and not modified) else obj.original
        key = utils.get_luxcore_name(source, is_viewport_render)
        if use_instancing:
            key += "_instance"
        return key

    def _convert_obj(self, exporter, dg_obj_instance, obj, depsgraph, luxcore_scene, scene_props, is_viewport_render):
        """ Convert one DepsgraphObjectInstance amd keep track of it """
        if obj.type == "EMPTY" or obj.data is None:
            return

        obj_key = utils.make_key_from_instance(dg_obj_instance)

        if obj.type in MESH_OBJECTS:
            # assert obj_key not in self.exported_objects
            self._convert_mesh_obj(exporter, dg_obj_instance, obj, obj_key, depsgraph,
                                   luxcore_scene, scene_props, is_viewport_render)
        elif obj.type == "LIGHT":
            props, exported_stuff = light.convert_light(exporter, obj, obj_key, depsgraph, luxcore_scene,
                                                        dg_obj_instance.matrix_world.copy(), is_viewport_render)
            if exported_stuff:
                self.exported_objects[obj_key] = exported_stuff
                scene_props.Set(props)

        # Convert hair
        for psys in obj.particle_systems:
            settings = psys.settings

            if settings.type == "HAIR" and settings.render_type == "PATH":
                convert_hair(exporter, obj, psys, depsgraph, luxcore_scene, is_viewport_render)

    def _convert_mesh_obj(self, exporter, dg_obj_instance, obj, obj_key, depsgraph,
                          luxcore_scene, scene_props, is_viewport_render):
        transform = dg_obj_instance.matrix_world

        use_instancing = is_viewport_render or dg_obj_instance.is_instance or utils.can_share_mesh(obj.original) \
                         or (exporter.motion_blur_enabled and obj.luxcore.enable_motion_blur)

        mesh_key = self._get_mesh_key(obj, use_instancing, is_viewport_render)
        # print(obj.name, "mesh key:", mesh_key)

        if use_instancing and mesh_key in self.exported_meshes:
            # print("retrieving mesh from cache")
            exported_mesh = self.exported_meshes[mesh_key]
        else:
            # print("fresh export")
            exported_mesh = mesh_converter.convert(obj, mesh_key, depsgraph, luxcore_scene,
                                                   is_viewport_render, use_instancing, transform)
            self.exported_meshes[mesh_key] = exported_mesh

        if exported_mesh:
            mat_names = []
            for idx, (shape_name, mat_index) in enumerate(exported_mesh.mesh_definitions):
                lux_mat_name, mat_props, use_pointiness = get_material(obj, mat_index, exporter, depsgraph, is_viewport_render)
                scene_props.Set(mat_props)
                mat_names.append(lux_mat_name)

                if use_pointiness:
                    # Replace shape definition with pointiness shape
                    pointiness_shape = shape_name + "_pointiness"
                    prefix = "scene.shapes." + pointiness_shape + "."
                    scene_props.Set(pyluxcore.Property(prefix + "type", "pointiness"))
                    scene_props.Set(pyluxcore.Property(prefix + "source", shape_name))
                    exported_mesh.mesh_definitions[idx] = [pointiness_shape, mat_index]

            obj_transform = transform.copy() if use_instancing else None

            if obj.luxcore.id == -1:
                obj_id = utils.make_object_id(dg_obj_instance)
            else:
                obj_id = obj.luxcore.id

            exported_obj = ExportedObject(obj_key, exported_mesh.mesh_definitions, mat_names,
                                          obj_transform, obj.luxcore.visible_to_camera, obj_id)
            scene_props.Set(exported_obj.get_props())
            self.exported_objects[obj_key] = exported_obj


    def diff(self, depsgraph):
        only_scene = len(depsgraph.updates) == 1 and isinstance(depsgraph.updates[0].id, bpy.types.Scene)
        return depsgraph.id_type_updated("OBJECT") and not only_scene

    def update(self, exporter, depsgraph, luxcore_scene, scene_props, is_viewport_render=True):
        print("object cache update")

        redefine_objs_with_these_mesh_keys = []
        # Always instance in viewport so we can move objects around
        use_instancing = True

        # Geometry updates (mesh edit, modifier edit etc.)
        if depsgraph.id_type_updated("OBJECT"):
            print("exported meshes:", self.exported_meshes.keys())

            for dg_update in depsgraph.updates:
                print(f"update id: {dg_update.id}, geom: {dg_update.is_updated_geometry}, trans: {dg_update.is_updated_transform}")

                if dg_update.is_updated_geometry and isinstance(dg_update.id, bpy.types.Object):
                    obj = dg_update.id
                    obj_key = utils.make_key(obj)

                    if obj.type in MESH_OBJECTS:
                        print(f"Geometry of obj {obj.name} was updated")
                        mesh_key = self._get_mesh_key(obj, use_instancing)

                        # if mesh_key not in self.exported_meshes:
                        # TODO this can happen if a deforming modifier is added
                        #  to an already-exported object. how to handle this case?

                        transform = None  # In viewport render, everything is instanced
                        exported_mesh = mesh_converter.convert(obj, mesh_key, depsgraph, luxcore_scene,
                                                               is_viewport_render, use_instancing, transform)
                        self.exported_meshes[mesh_key] = exported_mesh

                        # We arrive here not only when the mesh is edited, but also when the material
                        # of the object is changed in Blender. In this case we have to re-define all
                        # objects using this mesh (just the properties, the mesh is not re-exported).
                        redefine_objs_with_these_mesh_keys.append(mesh_key)
                    elif obj.type == "LIGHT":
                        print(f"Light obj {obj.name} was updated")
                        props, exported_stuff = light.convert_light(exporter, obj, obj_key, depsgraph, luxcore_scene,
                                                                    obj.matrix_world.copy(), is_viewport_render)
                        if exported_stuff:
                            self.exported_objects[obj_key] = exported_stuff
                            scene_props.Set(props)

        # TODO maybe not loop over all instances, instead only loop over updated
        #  objects and check if they have a particle system that needs to be updated?
        #  Would be better for performance with many particles, however I'm not sure
        #  we can find all instances corresponding to one particle system?

        # Currently, every update that doesn't require a mesh re-export happens here
        for dg_obj_instance in depsgraph.object_instances:
            obj = dg_obj_instance.instance_object if dg_obj_instance.is_instance else dg_obj_instance.object
            if not self._is_visible(dg_obj_instance, obj):
                continue

            obj_key = utils.make_key_from_instance(dg_obj_instance)
            mesh_key = self._get_mesh_key(obj, use_instancing)

            if (obj_key in self.exported_objects and obj.type != "LIGHT") and not mesh_key in redefine_objs_with_these_mesh_keys:
                exported_obj = self.exported_objects[obj_key]
                updated = False

                if exported_obj.transform != dg_obj_instance.matrix_world:
                    exported_obj.transform = dg_obj_instance.matrix_world.copy()
                    updated = True

                obj_id = utils.make_object_id(dg_obj_instance)
                if exported_obj.obj_id != obj_id:
                    exported_obj.obj_id = obj_id
                    updated = True

                if exported_obj.visible_to_camera != obj.luxcore.visible_to_camera:
                    exported_obj.visible_to_camera = obj.luxcore.visible_to_camera
                    updated = True

                if updated:
                    scene_props.Set(exported_obj.get_props())
            else:
                # Object is new and not in LuxCore yet, or it is a light, do a full export
                # TODO use luxcore_scene.DuplicateObjects for instances
                self._convert_obj(exporter, dg_obj_instance, obj, depsgraph,
                                  luxcore_scene, scene_props, is_viewport_render)

        self._debug_info()
