# FIXME: For some reason this doesn't work with multiple rules with the same input extension.
#from waflib import TaskGen
#TaskGen.declare_chain(name='hex', rule='${OBJCOPY} -O ihex ${SRC} ${TGT}', ext_in='.elf', ext_out='.hex')
#TaskGen.declare_chain(name='bin', rule='${OBJCOPY} -O binary ${SRC} ${TGT}', ext_in='.elf', ext_out='.bin')

def objcopy(task, mode):
    return task.exec_command('arm-none-eabi-objcopy -R .stack -R .bss -O %s %s %s' % (mode, task.inputs[0].abspath(), task.outputs[0].abspath()))

def objcopy_fill_bss(task, mode):
    return task.exec_command('arm-none-eabi-objcopy -O %s -j .text -j .data -j .bss --set-section-flags .bss=alloc,load,contents %s %s' % (mode, task.inputs[0].abspath(), task.outputs[0].abspath()))

def objcopy_hex(task):
    return objcopy(task, 'ihex')

def objcopy_bin(task):
    return objcopy(task, 'binary')
