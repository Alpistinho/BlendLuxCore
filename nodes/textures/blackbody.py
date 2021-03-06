import bpy
from bpy.props import FloatProperty
from ..base import LuxCoreNodeTexture
from ...utils import node as utils_node


class LuxCoreNodeTexBlackbody(bpy.types.Node, LuxCoreNodeTexture):
    bl_label = "Blackbody"
    bl_width_default = 200

    temperature: FloatProperty(update=utils_node.force_viewport_update, name="Temperature", description="Blackbody Temperature",
                                default=6500, min=0, soft_max=10000, step=10)
    
    def init(self, context):
        self.outputs.new("LuxCoreSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "temperature", slider=True)
    
    def sub_export(self, exporter, depsgraph, props, luxcore_name=None, output_socket=None):
        definitions = {
            "type": "blackbody",
            "temperature": self.temperature,
        }       
        
        return self.create_props(props, definitions, luxcore_name)
