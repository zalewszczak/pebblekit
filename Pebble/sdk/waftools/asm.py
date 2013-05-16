from waflib import Task
from waflib.TaskGen import extension

class asm(Task.Task):
    color = 'BLUE'
    run_str = '${AS} ${ASFLAGS} -c ${SRC} -o ${TGT}'

@extension('.s')
def asm_hook(self,node):
    return self.create_compiled_task('asm',node)
