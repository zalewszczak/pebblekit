def configure(conf):
    CROSS_COMPILE_PREFIX = 'arm-none-eabi-'

    conf.env.AS = CROSS_COMPILE_PREFIX + 'gcc'
    conf.env.AR = CROSS_COMPILE_PREFIX + 'ar'
    if conf.options.use_clang:
      conf.env.CC = '/home/brad/src/builddebug/Debug+Asserts/bin/clang'
    else:
      conf.env.CC = CROSS_COMPILE_PREFIX + 'gcc'
    conf.env.LD = CROSS_COMPILE_PREFIX + 'ld'

    conf.load('gcc')

    conf.env.append_value('CFLAGS', [ '-std=c99',
                                      '-mcpu=cortex-m3',
                                      '-mthumb',
                                      '-fdata-sections',
                                      '-ffunction-sections',
                                      '-g' ])

    c_warnings = [ '-Wall',
                   '-Wextra',
                   '-Werror',
                   '-Wno-unused-parameter',
                   '-Wno-missing-field-initializers',
                   '-Wno-error=unused-function',
                   '-Wno-error=unused-variable',
                   '-Wno-error=unused-parameter' ]

    if conf.options.use_clang:
      conf.env.append_value('CFLAGS', [ '-target', 'arm-none-eabi' ])
      conf.env.append_value('CFLAGS', [ '--sysroot', '/home/brad/arm-cs-tools/arm-none-eabi' ])

      conf.env.append_value('LINKFLAGS', [ '-target', 'arm-none-eabi' ])
      conf.env.append_value('LINKFLAGS', [ '--sysroot', '/home/brad/arm-cs-tools/arm-none-eabi' ])
    else:
      # This warning only exists in GCC
      c_warnings.append('-Wno-error=unused-but-set-variable')

    conf.env.append_value('CFLAGS', c_warnings)

    conf.env.append_value('DEFINES', [ 'USE_STDPERIPH_DRIVER=1',
                                       'BOARD_' + conf.options.board.upper(),
                                       '_ARCH_CORTEX_M3', ])

    conf.env.ASFLAGS = [ '-mcpu=cortex-m3',
                         '-mthumb',
                         '-xassembler-with-cpp' ]

    conf.env.append_value('LINKFLAGS', [ '-mcpu=cortex-m3',
                                         '-mthumb',
                                         '-Wl,--warn-common' ])

    conf.env.SHLIB_MARKER = None
    conf.env.STLIB_MARKER = None

    if conf.env.BOOTLOADER:
        optimize_flags = '-Os'
        conf.env.append_value('DEFINES', 'BOOTLOADER')

        print "Bootloader, forcing -Os"
    elif conf.options.release:
        optimize_flags = '-Os'

        # FIXME: Turn this off for released builds???
        conf.env.append_value('DEFINES', 'PBL_LOG_ENABLED')

        conf.env.append_value('DEFINES', 'RELEASE')
        print "Release mode"
    elif conf.options.fat_firmware:
        optimize_flags = '-O0'
        conf.env.append_value('DEFINES', 'PBL_LOG_ENABLED')
        conf.env.IS_FAT_FIRMWARE = True
        print 'Building Fat Firmware (no optimizations, logging enabled)'
    elif conf.options.gdb:
        optimize_flags = '-O0'
        print "GDB mode"
    else:
        optimize_flags = '-Os'
        conf.env.append_value('DEFINES', 'PBL_LOG_ENABLED')
        print 'Debug Mode'

    if conf.options.malloc_instrumentation:
        conf.env.append_value('LINKFLAGS', [ '-Wl,--wrap=malloc',
                                             '-Wl,--undefined=__wrap_malloc',
                                             '-Wl,--wrap=realloc',
                                             '-Wl,--undefined=__wrap_realloc',
                                             '-Wl,--wrap=free',
                                             '-Wl,--undefined=__wrap_free' ])
        conf.env.append_value('DEFINES', 'MALLOC_INSTRUMENTATION')
        print "Enabling malloc instrumentation"

    conf.env.append_value('CFLAGS', optimize_flags)
    conf.env.append_value('LINKFLAGS', optimize_flags)
