
def ragel(task):
    task.exec_command('ragel -o %s -C %s' % (task.outputs[0].abspath(), task.inputs[0].abspath()))
