# from bl_ui.properties_render import RenderButtonsPanel
# from bpy.types import Panel
# from .. import utils
# from . import icons
#
#
# class LUXCORE_RENDER_PT_viewport_settings(RenderButtonsPanel, Panel):
#     COMPAT_ENGINES = {"LUXCORE"}
#     bl_label = "LuxCore Viewport Settings"
#     bl_options = {"DEFAULT_CLOSED"}
#
#     @classmethod
#     def poll(cls, context):
#         return context.scene.render.engine == "LUXCORE"
#
#     def draw(self, context):
#         layout = self.layout
#         viewport = context.scene.luxcore.viewport
#
#         layout.prop(viewport, "halt_time")
#         layout.prop(viewport, "reduce_resolution_on_edit")
#
#         col = layout.column()
#         col.prop(viewport, "pixel_size")
#         sub = col.column()
#         sub.active = viewport.pixel_size != "1"
#         sub.prop(viewport, "mag_filter")
#
#         luxcore_engine = context.scene.luxcore.config.engine
#
#         if luxcore_engine == "BIDIR":
#             layout.prop(viewport, "use_bidir")
#
#         if not (luxcore_engine == "BIDIR" and viewport.use_bidir):
#             row = layout.row()
#             row.label(text="Device:")
#             row.prop(viewport, "device", expand=True)
#
#             if viewport.device == "OCL" and not utils.is_opencl_build():
#                 layout.label(text="No OpenCL support in this BlendLuxCore version", icon=icons.ERROR)
#                 layout.label(text="(Falling back to CPU realtime engine)")
