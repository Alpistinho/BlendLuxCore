import bpy
from bpy.props import FloatProperty
from .. import LuxCoreNodeMaterial
from ..sockets import LuxCoreSocketFloat

SIGMA_DESCRIPTION = "Surface roughness, 0 for pure Lambertian reflection"


class LuxCoreSocketSigma(LuxCoreSocketFloat, bpy.types.NodeSocket):
    default_value: FloatProperty(min=0, max=45, description=SIGMA_DESCRIPTION)
    slider = True


class LuxCoreNodeMatMatte(LuxCoreNodeMaterial, bpy.types.Node):
    """(Rough) matte material node"""
    bl_label = "Matte Material"
    bl_width_default = 160

    def init(self, context):
        self.add_input("LuxCoreSocketColor", "Diffuse Color", (0.7, 0.7, 0.7))
        self.add_input("LuxCoreSocketSigma", "Sigma", 0)
        self.add_common_inputs()

        self.outputs.new("LuxCoreSocketMaterial", "Material")

    def sub_export(self, exporter, props, luxcore_name=None):
        definitions = {
            "type": "roughmatte",
            "kd": self.inputs["Diffuse Color"].export(exporter, props),
            "sigma": self.inputs["Sigma"].export(exporter, props),
        }
        self.export_common_inputs(exporter, props, definitions)
        return self.create_props(props, definitions, luxcore_name)
