import bpy
from bpy.types import NodeTree
import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem, NodeItemCustom
from ...ui import icons
from ...utils import node as utils_node
from ..nodeitems import Separator, NodeItemMultiImageImport
from .. import LuxCoreNodeTree


class LuxCoreMaterialNodeTree(LuxCoreNodeTree, NodeTree):
    bl_idname = "luxcore_material_nodes"
    bl_label = "LuxCore Material Nodes"
    bl_icon = icons.NTREE_MATERIAL

    @classmethod
    def get_from_context(cls, context):
        """
        Switches the displayed node tree when user selects object/material
        """
        obj = context.active_object

        if obj and obj.type not in {"LAMP", "CAMERA"}:
            mat = obj.active_material

            if mat:
                # ID pointer
                node_tree = mat.luxcore.node_tree

                if node_tree:
                    return node_tree, mat, mat

        return None, None, None

    # This block updates the preview, when socket links change
    def update(self):
        super().update()

        # Update opengl materials in case the node linked to the
        # output has changed
        utils_node.update_opengl_materials(None, bpy.context)


class LuxCoreNodeCategoryMaterial(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == "luxcore_material_nodes"


# Here we define the menu structure the user sees when he
# presses Shift+A in the node editor to add a new node.
# In general it is a good idea to put often used nodes near the top.
luxcore_node_categories_material = [
    LuxCoreNodeCategoryMaterial("LUXCORE_MATERIAL_MATERIAL", "Material", items=[
        NodeItem("LuxCoreNodeMatMix", label="Mix"),
        NodeItem("LuxCoreNodeMatMatte", label="Matte"),
        NodeItem("LuxCoreNodeMatMatteTranslucent", label="Matte Translucent"),
        NodeItem("LuxCoreNodeMatMetal", label="Metal"),
        NodeItem("LuxCoreNodeMatMirror", label="Mirror"),
        NodeItem("LuxCoreNodeMatGlossy2", label="Glossy"),
        NodeItem("LuxCoreNodeMatGlossyTranslucent", label="Glossy Translucent"),
        NodeItem("LuxCoreNodeMatGlossyCoating", label="Glossy Coating"),
        NodeItem("LuxCoreNodeMatGlass", label="Glass"),
        NodeItem("LuxCoreNodeMatNull", label="Null (Transparent)"),
        NodeItem("LuxCoreNodeMatCarpaint", label="Carpaint"),
        NodeItem("LuxCoreNodeMatCloth", label="Cloth"),
        NodeItem("LuxCoreNodeMatVelvet", label="Velvet"),
    ]),

    LuxCoreNodeCategoryMaterial("LUXCORE_MATERIAL_TEXTURE", "Texture", items=[
        NodeItemMultiImageImport(),
        NodeItem("LuxCoreNodeTexImagemap", label="Image"),
        Separator(),
        # Procedurals
        NodeItem("LuxCoreNodeTexBrick", label="Brick"),
        NodeItem("LuxCoreNodeTexDots", label="Dots"),
        NodeItem("LuxCoreNodeTexfBM", label="fBM"),
        NodeItem("LuxCoreNodeTexCheckerboard2D", label="2D Checkerboard"),
        NodeItem("LuxCoreNodeTexCheckerboard3D", label="3D Checkerboard"),
        NodeItem("LuxCoreNodeTexMarble", label="Marble"),
        # NodeItem("LuxCoreNodeTexWindy", label="Windy"),  # Same as FBM -> unnecessary
        NodeItem("LuxCoreNodeTexWrinkled", label="Wrinkled"),
        Separator(),
        NodeItem("LuxCoreNodeTexHitpoint", label="Vertex Color"),
        NodeItem("LuxCoreNodeTexSmoke", label="Smoke Data"),
        NodeItem("LuxCoreNodeTexFresnel", label="Fresnel"),
    ]),

    LuxCoreNodeCategoryMaterial("LUXCORE_MATERIAL_BLENDERTEXTURE", "Texture (Blender)", items=[
        NodeItem("LuxCoreNodeTexBlenderBlend", label="Blend"),
        NodeItem("LuxCoreNodeTexBlenderClouds", label="Clouds"),
        NodeItem("LuxCoreNodeTexBlenderDistortedNoise", label="Distorted Noise"),
        NodeItem("LuxCoreNodeTexBlenderMagic", label="Magic"),
        NodeItem("LuxCoreNodeTexBlenderMarble", label="Marble"),
        NodeItem("LuxCoreNodeTexBlenderMusgrave", label="Musgrave"),
        NodeItem("LuxCoreNodeTexBlenderNoise", label="Noise"),
        NodeItem("LuxCoreNodeTexBlenderStucci", label="Stucci"),
        NodeItem("LuxCoreNodeTexBlenderWood", label="Wood"),
        NodeItem("LuxCoreNodeTexBlenderVoronoi", label="Voronoi"),
    ]),

    LuxCoreNodeCategoryMaterial("LUXCORE_MATERIAL_UTILS", "Utils", items=[
        NodeItem("LuxCoreNodeTexColorMix", label="ColorMix"),
        NodeItem("LuxCoreNodeTexMath", label="Math"),
        NodeItem("LuxCoreNodeTexRemap", label="Remap"),
        NodeItem("LuxCoreNodeTexInvert", label="Invert"),
        Separator(),
        NodeItem("LuxCoreNodeTexBump", label="Bump"),
        # Possibly confusing, better deactivate (only needed in very rare cases anyway)
        # NodeItem("LuxCoreNodeTexNormalmap", label="Normalmap"),
        NodeItem("LuxCoreNodeTexBand", label="Band"),
        NodeItem("LuxCoreNodeTexHSV", label="HSV"),
        NodeItem("LuxCoreNodeTexConstfloat1", label="Constant Value"),
        NodeItem("LuxCoreNodeTexConstfloat3", label="Constant Color"),
        NodeItem("LuxCoreNodeTexPointiness", label="Pointiness"),
        NodeItem("LuxCoreNodeTexObjectID", label="Object ID"),
        NodeItem("LuxCoreNodeTexUV", label="UV Test"),
        NodeItem("LuxCoreNodeTexIORPreset", label="IOR Preset"),
    ]),

    LuxCoreNodeCategoryMaterial("LUXCORE_MATERIAL_MAPPING", "Mapping", items=[
        NodeItem("LuxCoreNodeTexMapping2D", label="2D Mapping"),
        NodeItem("LuxCoreNodeTexMapping3D", label="3D Mapping"),
    ]),

    LuxCoreNodeCategoryMaterial("LUXCORE_MATERIAL_LIGHT", "Light", items=[
        NodeItem("LuxCoreNodeMatEmission", label="Light Emission"),
        Separator(),
        NodeItem("LuxCoreNodeTexLampSpectrum", label="Lamp Spectrum"),
        NodeItem("LuxCoreNodeTexBlackbody", label="Lamp Blackbody Temperature"),
        NodeItem("LuxCoreNodeTexIrregularData", label="Irregular Data"),
    ]),

    LuxCoreNodeCategoryMaterial("LUXCORE_MATERIAL_POINTER", "Pointer", items=[
        NodeItem("LuxCoreNodeTreePointer", label="Pointer"),
    ]),

    LuxCoreNodeCategoryMaterial("LUXCORE_MATERIAL_OUTPUT", "Output", items=[
        NodeItem("LuxCoreNodeMatOutput", label="Output"),
    ]),

    LuxCoreNodeCategoryMaterial("LUXCORE_MATERIAL_LAYOUT", "Layout", items=[
        NodeItem("NodeFrame", label="Frame"),
        NodeItem("NodeReroute", label="Reroute"),
    ]),
]


def register():
    nodeitems_utils.register_node_categories("LUXCORE_MATERIAL_TREE", luxcore_node_categories_material)
    print("material nodes registered")


def unregister():
    nodeitems_utils.unregister_node_categories("LUXCORE_MATERIAL_TREE")
    print("material nodes unregistered")
