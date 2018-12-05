
try:
    from .bin import pyluxcore
except ImportError as error:
    msg = "\n\nCould not import pyluxcore."
    import platform
    if platform.system() == "Windows":
        msg += ("\nYou probably forgot to install one of the "
                "redistributable packages.\n"
                "They are listed in the release announcement post.")
    # Raise from None to suppress the unhelpful
    # "during handling of the above exception, ..."
    raise Exception(msg + "\n\nImportError: %s" % error) from None

# import bpy
# Have to import everything with classes which need to be registered
# from . import engine, handlers, nodes, operators, properties, ui
# from .nodes import materials, volumes, textures
# from .ui import (
#     aovs, blender_object, camera, config, debug, denoiser, device, display,
#     errorlog, halt, image_tools, light, lightgroups, material, particle,
#     postpro, render, render_layer, scene, texture, units, viewport, world,
# )
# from .utils.log import LuxCoreLog

bl_info = {
    "name": "LuxCore",
    "author": "Simon Wendsche (B.Y.O.B.), Michael Klemm (neo2068), Philstix",
    "version": (2, 1),
    "blender": (2, 80, 0),
    "category": "Render",
    "location": "Info header, render engine menu",
    "description": "LuxCore integration for Blender",
    "warning": "beta2",
    "wiki_url": "https://wiki.luxcorerender.org/",
    "tracker_url": "https://github.com/LuxCoreRender/BlendLuxCore/issues/new",
}


# def register():
#     # handlers.register()
#     nodes.materials.register()
#     nodes.textures.register()
#     nodes.volumes.register()
#     # bpy.utils.register_module(__name__)
#     ui.register()
#
#     properties.init()
#
#     # Has to be called at least once, can be called multiple times
#     pyluxcore.Init(LuxCoreLog.add)
#     print("pyluxcore version:", pyluxcore.Version())
#
#
# def unregister():
#     # handlers.unregister()
#     ui.unregister()
#     nodes.materials.unregister()
#     nodes.textures.unregister()
#     nodes.volumes.unregister()
#     # bpy.utils.unregister_module(__name__)

from . import auto_load, nodes, properties, ui
from .nodes import materials, volumes, textures

auto_load.init()


def register():
    auto_load.register()
    nodes.materials.register()
    nodes.textures.register()
    nodes.volumes.register()
    ui.register()

    properties.init()

    from .utils.log import LuxCoreLog
    pyluxcore.Init(LuxCoreLog.add)
    print("BlendLuxCore registered (%s)" % pyluxcore.Version())


def unregister():
    auto_load.unregister()
    nodes.materials.unregister()
    nodes.textures.unregister()
    nodes.volumes.unregister()
    print("BlendLuxCore unregistered")
