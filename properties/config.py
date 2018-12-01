import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    EnumProperty, BoolProperty, IntProperty, FloatProperty,
    PointerProperty, StringProperty,
)
from math import radians


TILED_DESCRIPTION = (
    "Render the image in quadratic chunks instead of sampling the whole film at once;\n"
    "Causes lower memory usage; Uses a special sampler"
)
TILE_SIZE_DESC = (
    "Note that OpenCL devices will automatically render multiple tiles if it increases performance"
)

AA_SAMPLE_DESC = (
    "How many AA samples to compute per pass. Higher values increase memory usage, but lead to better performance. "
    "Note that this number is squared, so e.g. a value of 5 will lead to 25 samples per pixel after one pass"
)

THRESH_REDUCT_DESC = (
    "Multiply noise level with this value after all tiles have converged, "
    "then continue with the lowered noise level"
)
THRESH_WARMUP_DESC = "How many samples to render before starting the convergence tests"

SIMPLE_DESC = "Recommended for scenes with simple lighting (outdoors, studio setups, indoors with large windows)"
COMPLEX_DESC = "Recommended for scenes with difficult lighting (caustics, indoors with small windows)"

FILTER_DESC = (
    "Pixel filtering slightly blurs the image, which reduces noise and \n"
    "fireflies and leads to a more realistic image impression;\n"
    "When using OpenCL, disabling this option can increase rendering speed"
)
FILTER_WIDTH_DESC = "Filter width in pixels; lower values result in a sharper image, higher values smooth out noise"

CLAMPING_DESC = (
    "Use to reduce fireflies. The optimal clamping value is computed after "
    "rendering for 10 seconds, but only if clamping is DISABLED"
)

SEED_DESC = (
    "Seed for random number generation. Images rendered with "
    "the same seed will have the same noise pattern"
)
ANIM_SEED_DESC = "Use different seed values for different frames"

SOBOL_ADAPTIVE_STRENGTH_DESC = (
    "A value of 0 means that each pixel is sampled equally, higher values "
    "focus more samples on noisy areas of the image"
)

LOG_POWER_DESC = (
    "(Default) Sample lights according to their brightness, but weighting very bright "
    "lights not much more than dim lights (recommended when using environment "
    "lights (HDRI/sky) plus few small light sources)"
)

POWER_DESC = (
    "Sample lights according to their brightness (recommended when using very bright "
    "lights (e.g. sun) together with highpoly meshlights with more than about 10 tris)"
)

UNIFORM_DESC = "Sample all lights equally, not according to their brightness"

DLSC_DESC = (
    "Use the DLSC in scenes with many light sources if each of them only "
    "lights up a small part of the scene (example: a city at night). "
    "The DLSC is built before the rendering starts"
)

LARGE_STEP_RATE_DESC = (
    "Probability of generating a large sample mutation. "
    "Low values cause the sampler to focus more on "
    "caustics and other hotspots it found, while high "
    "values make the sampler behave more like a pure "
    "random sampler"
)

MAX_CONSECUTIVE_REJECT_DESC = (
    "Number of consecutive rejects before a next "
    "mutation is forced. Low values can cause bias"
)

IMAGE_MUTATION_RATE_DESC = "Maximum distance over the image plane for a small mutation"


class LuxCoreConfigPath(PropertyGroup):
    """
    path.*
    Stored in LuxCoreConfig, accesss with scene.luxcore.config.path
    """
    # TODO: helpful descriptions
    # path.pathdepth.total
    depth_total: IntProperty(name="Total Path Depth", default=6, min=1, soft_max=16)
    # path.pathdepth.diffuse
    depth_diffuse: IntProperty(name="Diffuse", default=4, min=1, soft_max=16)
    # path.pathdepth.glossy
    depth_glossy: IntProperty(name="Glossy", default=4, min=1, soft_max=16)
    # path.pathdepth.specular
    depth_specular: IntProperty(name="Specular", default=6, min=1, soft_max=16)

    use_clamping: BoolProperty(name="Clamp Output", default=False, description=CLAMPING_DESC)
    # path.clamping.variance.maxvalue
    clamping: FloatProperty(name="Max Brightness", default=1000, min=0, description=CLAMPING_DESC)
    # This should only be set in the engine code after export. Only show a read-only label to the user.
    suggested_clamping_value: FloatProperty(name="", default=-1)

    # We probably don't need to expose these properties because they have good
    # default values that should very rarely (or never?) need adjustment
    # path.russianroulette.depth
    # path.russianroulette.cap


class LuxCoreConfigTile(PropertyGroup):
    """
    tile.*
    Stored in LuxCoreConfig, accesss with scene.luxcore.config.tile
    """
    # tilepath.sampling.aa.size
    path_sampling_aa_size: IntProperty(name="AA Samples", default=3, min=1, soft_max=13,
                                        description=AA_SAMPLE_DESC)

    # tile.size
    size: IntProperty(name="Tile Size", default=64, min=16, soft_min=32, soft_max=256, subtype="PIXEL",
                       description=TILE_SIZE_DESC)

    # tile.multipass.enable
    multipass_enable: BoolProperty(name="Multipass", default=True, description="")

    # TODO: unify with halt condition noise threshold settings

    # tile.multipass.convergencetest.threshold
    multipass_convtest_threshold: FloatProperty(name="Convergence Threshold", default=(6 / 256),
                                                 min=0.0000001, soft_max=(6 / 256),
                                                 description="")
    # tile.multipass.convergencetest.threshold.reduction
    multipass_convtest_threshold_reduction: FloatProperty(name="Threshold Reduction", default=0.5, min=0.001,
                                                           soft_min=0.1, max=0.99, soft_max=0.9,
                                                           description=THRESH_REDUCT_DESC)
    # tile.multipass.convergencetest.warmup.count
    multipass_convtest_warmup: IntProperty(name="Convergence Warmup", default=32, min=0,
                                            soft_min=8, soft_max=128,
                                            description=THRESH_WARMUP_DESC)


class LuxCoreConfigDLSCache(PropertyGroup):
    show_advanced: BoolProperty(name="Show Advanced", default=False)

    # TODO min/max, descriptions
    entry_radius: FloatProperty(name="Entry Radius", default=0.15, min=0, subtype="DISTANCE",
                                 description="Choose this value according to the size of your scene. "
                                             "The default (15 cm) is suited for a room-sized scene")
    entry_normalangle: FloatProperty(name="Normal Angle",
                                      default=radians(10), min=0, max=radians(90), subtype="ANGLE")
    entry_maxpasses: IntProperty(name="Max. Passes", default=1024, min=0)
    entry_convergencethreshold: FloatProperty(name="Convergence Threshold",
                                               default=1, min=0, max=100, subtype="PERCENTAGE")
    entry_warmupsamples: IntProperty(name="Warmup Samples", default=12, min=0,
                                      description="Increase this value if splotchy artifacts appear in the image")
    entry_volumes_enable: BoolProperty(name="Place Entries in Volumes", default=False,
                                        description="Enable/disable placement of entries in volumes (in mid-air)")

    lightthreshold: FloatProperty(name="Light Threshold", default=1, min=0, max=100, subtype="PERCENTAGE")
    targetcachehitratio: FloatProperty(name="Target Cache Hit Ratio",
                                        default=99.5, min=0, max=100, subtype="PERCENTAGE")
    maxdepth: IntProperty(name="Max. Depth", default=4, min=0)
    maxsamplescount: IntProperty(name="Max. Samples", default=10000000, min=0)


class LuxCoreConfig(PropertyGroup):
    """
    Main config storage class.
    Access (in ui or export) with scene.luxcore.config
    """

    # These settings are mostly not directly transferrable to LuxCore properties
    # They need some if/else decisions and aggregation, e.g. to build the engine name from parts
    engines = [
        ("PATH", "Path", "Unidirectional path tracer; " + SIMPLE_DESC, 0),
        ("BIDIR", "Bidir", "Bidirectional path tracer; " + COMPLEX_DESC, 1),
    ]
    engine: EnumProperty(name="Engine", items=engines, default="PATH")

    # Only available when tiled rendering is off
    samplers = [
        ("SOBOL", "Sobol", SIMPLE_DESC, 0),
        ("METROPOLIS", "Metropolis", COMPLEX_DESC, 1),
        ("RANDOM", "Random", "Recommended only if the denoiser is used", 2),
    ]
    sampler: EnumProperty(name="Sampler", items=samplers, default="SOBOL")

    # SOBOL properties
    sobol_adaptive_strength: FloatProperty(name="Adaptive Strength", default=0.7, min=0, max=0.95,
                                            description=SOBOL_ADAPTIVE_STRENGTH_DESC)
    # METROPOLIS properties
    # sampler.metropolis.largesteprate
    metropolis_largesteprate: FloatProperty(name="Large Mutation Probability", default=40,
                                             min=0, max=100, precision=0, subtype="PERCENTAGE",
                                             description=LARGE_STEP_RATE_DESC)
    # sampler.metropolis.maxconsecutivereject
    metropolis_maxconsecutivereject: IntProperty(name="Max Consecutive Rejects", default=512, min=0,
                                                  description=MAX_CONSECUTIVE_REJECT_DESC)
    # sampler.metropolis.imagemutationrate
    metropolis_imagemutationrate: FloatProperty(name="Image Mutation Rate", default=10,
                                                 min=0, max=100, precision=0, subtype="PERCENTAGE",
                                                 description=IMAGE_MUTATION_RATE_DESC)

    # Only available when engine is PATH (not BIDIR)
    devices = [
        ("CPU", "CPU", "Use the arithmetic logic units in your central processing unit", 0),
        ("OCL", "OpenCL", "Use the good ol' pixel cruncher", 1),
    ]
    device: EnumProperty(name="Device", items=devices, default="CPU")
    # A trick so we can show the user that bidir can only be used on the CPU (see UI code)
    bidir_device: EnumProperty(name="Device", items=devices, default="CPU",
                                description="Bidir only available on CPU")

    use_tiles: BoolProperty(name="Tiled", default=False, description=TILED_DESCRIPTION)

    # Special properties of the various engines
    path: PointerProperty(type=LuxCoreConfigPath)
    tile: PointerProperty(type=LuxCoreConfigTile)
    # BIDIR properties
    # light.maxdepth
    bidir_light_maxdepth: IntProperty(name="Light Depth", default=10, min=1, soft_max=16)
    # path.maxdepth
    bidir_path_maxdepth: IntProperty(name="Eye Depth", default=10, min=1, soft_max=16)

    # Pixel filter
    filters = [
        ("BLACKMANHARRIS", "Blackman-Harris", "Default, usually the best option", 0),
        ("MITCHELL_SS", "Mitchell", "Sharp, but can produce black ringing artifacts around bright pixels", 1),
        ("GAUSSIAN", "Gaussian", "Blurry", 2),
        ("NONE", "None", "Disable pixel filtering. Fastest setting when rendering on GPU", 3)
    ]
    filter: EnumProperty(name="Filter", items=filters, default="BLACKMANHARRIS",
                          description=FILTER_DESC)
    filter_width: FloatProperty(name="Filter Width", default=1.5, min=0.5, soft_max=3,
                                 description=FILTER_WIDTH_DESC, subtype="PIXEL")
    gaussian_alpha: FloatProperty(name="Gaussian Filter Alpha", default=2, min=0.1, max=10,
                                   description="Gaussian rate of falloff. Lower values give blurrier images")

    # Light strategy
    light_strategy_items = [
        ("LOG_POWER", "Log Power", LOG_POWER_DESC, 0),
        ("POWER", "Power", POWER_DESC, 1),
        ("UNIFORM", "Uniform", UNIFORM_DESC, 2),
        ("DLS_CACHE", "Direct Light Sampling Cache", DLSC_DESC, 3),
    ]
    light_strategy: EnumProperty(name="Light Strategy", items=light_strategy_items, default="LOG_POWER",
                                  description="Decides how the lights in the scene are sampled")

    # Special properties of the direct light sampling cache
    dls_cache: PointerProperty(type=LuxCoreConfigDLSCache)

    # FILESAVER options
    use_filesaver: BoolProperty(name="Only write LuxCore scene", default=False)
    filesaver_format_items = [
        ("TXT", "Text", "Save as .scn and .cfg text files", 0),
        ("BIN", "Binary", "Save as .bcf binary file", 1),
    ]
    filesaver_format: EnumProperty(name="", items=filesaver_format_items, default="BIN")
    filesaver_path: StringProperty(name="", subtype="DIR_PATH")

    # Seed
    seed: IntProperty(name="Seed", default=1, min=1, description=SEED_DESC)
    use_animated_seed: BoolProperty(name="Animated Seed", default=False, description=ANIM_SEED_DESC)

    # Min. epsilon settings (drawn in ui/units.py)
    show_min_epsilon: BoolProperty(name="Advanced LuxCore Settings", default=False,
                                    description="Show/Hide advanced LuxCore features. "
                                                "Only change them if you know what you are doing")
    min_epsilon: FloatProperty(name="Min. Epsilon", default=1e-5, soft_min=1e-6, soft_max=1e-1,
                                precision=5,
                                description="User higher values when artifacts due to floating point precision "
                                            "issues appear in the rendered image")
    max_epsilon: FloatProperty(name="Max. Epsilon", default=1e-1, soft_min=1e-3, soft_max=1e+2,
                                precision=5,
                                description="Might need adjustment along with the min epsilon to avoid "
                                            "artifacts due to floating point precision issues")

    film_opencl_enable: BoolProperty(name="Use OpenCL", default=True,
                                      description="Use OpenCL to accelerate tonemapping and other imagepipeline "
                                                  "operations (applies to viewport and final render). "
                                                  "Disabling this option will save a bit of RAM, especially if "
                                                  "the render resolution is large. "
                                                  "This option is ignored in Non-OpenCL builds")
