from waflib.TaskGen import before, after, feature
from waflib import Errors, Logs, Options, Task, Utils, Node
import os

@feature('pebble_test')
@after('apply_link')
def make_test(self):
    if not 'cprogram' in self.features and not 'cxxprogram' in self.features:
        Logs.error('test cannot be executed %s'%self)
        return
    if getattr(self, 'link_task', None):
      self.create_task('run_test', self.link_task.outputs)

# Lock to prevent concurrent modifications of the utest_results list. We may
# have multiple tests running and finishing at the same time.
import threading
testlock = threading.Lock()

class run_test(Task.Task):
    color = 'PINK'

    def runnable_status(self):
        ret = super(run_test, self).runnable_status()
        if ret==Task.SKIP_ME:
          # FIXME: We probably don't need to rerun tests if the inputs don't change, but meh, whatever.
          return Task.RUN_ME
        return ret

    def run(self):
        filename = self.inputs[0].abspath()
        cwd = self.inputs[0].parent.abspath()

        try:
          proc = Utils.subprocess.Popen(filename, cwd=cwd, stderr=Utils.subprocess.PIPE, stdout=Utils.subprocess.PIPE)
          (stdout, stderr) = proc.communicate()
        except OSError:
          Logs.pprint('RED', 'Failed to run test: %s' % filename)
          return

        tup = (filename, proc.returncode, stdout, stderr)
        self.generator.utest_result = tup

        testlock.acquire()
        try:
            bld = self.generator.bld
            Logs.debug("ut: %r", tup)
            try:
                bld.utest_results.append(tup)
            except AttributeError:
                bld.utest_results = [tup]

            a = getattr(self.generator.bld, 'added_post_fun', False)
            if not a:
                self.generator.bld.add_post_fun(summary)
                self.generator.bld.added_post_fun = True
        finally:
            testlock.release()

def summary(bld):
    lst = getattr(bld, 'utest_results', [])

    if not lst: return

    total = len(lst)
    fail = len([x for x in lst if x[1]])

    Logs.pprint('CYAN', 'test summary')
    Logs.pprint('CYAN', '  tests that pass %d/%d' % (total-fail, total))

    for (f, code, out, err) in lst:
        if not code:
            Logs.pprint('GREEN', '    %s' % f)

    if fail>0:
        Logs.pprint('RED', '  tests that fail %d/%d' % (fail, total))
        for (f, code, out, err) in lst:
            if code:
                Logs.pprint('RED', '    %s' % f)
                print(out.decode('utf-8'))
        raise Errors.WafError('test failed')

def add_clar_test(bld, test_source, product_sources):
    # Fixme: waf isn't able to figure out the dependencies/ordering between the clar generator and the compilation step
    # By setting concurrent jobs to 1, race conditions are avoided as a work around:
    bld.jobs = 1

    # clar_main.c is generated in build_dir/test_dir/clar_main.c
    test_dir = test_source.path_from(bld.path.get_src())
    test_dir = test_dir[:-2] # Scrape off the extension
    test_dir_node = bld.path.get_bld().make_node(test_dir)

    clar_harness = test_dir_node.make_node('clar_main.c')

    # Should make this a general task like the objcopy ones.
    bld(rule='python ${CLAR_DIR}/clar.py --file=${SRC} --clar-path=${CLAR_DIR} %s' % test_dir_node.abspath(),
        source=test_source,
        target=clar_harness)

    Logs.debug("ut: Product sources %r", product_sources)

    test_bin = test_dir_node.make_node('runme')

    sources = [ test_source, clar_harness ]
    sources.extend(product_sources)
    src_includes = ["src/core",
        "src/fw",
        "src/boot",
        "src/fw/vendor/pebble_freertos/Source/include",
        "src/fw/vendor/pebble_freertos/Source/portable/GCC/" + bld.env.FREERTOS_PORT_FOLDER_NAME,
        "src/fw/vendor/Bluetopia/include",
        "src/fw/vendor/Bluetopia/btpskrnl" ]
    src_includes = [os.path.join(bld.srcnode.abspath(), f) for f in src_includes]
    bld.program(source=sources,
                target=test_bin,
                features='pebble_test',
                includes=[test_dir_node.abspath()] + src_includes)

def clar(bld, sources=None, sources_ant_glob=None, test_sources_ant_glob=None):
    if test_sources_ant_glob is None:
      raise Exception()

    product_sources = []
    if sources is not None:
      product_sources.extend(sources)
    if sources_ant_glob is not None:
      product_sources.extend(bld.srcnode.ant_glob(sources_ant_glob))

    test_sources = bld.path.ant_glob(test_sources_ant_glob)
    test_sources = [s for s in test_sources if not os.path.basename(s.abspath()).startswith('clar')]

    Logs.debug("ut: Test sources %r", test_sources)
    if len(test_sources) == 0:
        Logs.pprint('RED', 'No tests found for glob: %s' % test_sources_ant_glob)

    for test_source in test_sources:
        add_clar_test(bld, test_source, product_sources)

