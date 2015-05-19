#!/usr/bin/env python

"""
    TODO:

    Extract/merge same code parts with:

    https://github.com/jedie/pypyjs/blob/selenium/tests/test_console.py
"""

from __future__ import absolute_import, print_function

import difflib
import os
import posixpath
import pprint
import textwrap
import traceback
import unittest
import sys

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoAlertPresentException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait


def make_diff(block1, block2):
    d = difflib.Differ()

    block1 = block1.replace("\\n", "\\n\n").split("\n")
    block2 = block2.replace("\\n", "\\n\n").split("\n")

    diff = d.compare(block1, block2)

    result = ["%2s %s\n" % (line, i) for line, i in enumerate(diff)]
    return "".join(result)


def website_path(sub_path):
    path = posixpath.abspath(posixpath.join(os.path.dirname(__file__), "..", "website", sub_path))
    assert os.path.exists(path), "path %r doesn't exists!" % path
    return path


class BaseSeleniumTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(BaseSeleniumTestCase, cls).setUpClass()
        cls.driver = webdriver.Firefox()
        cls.driver.set_window_size(800, 900)
        cls.driver.set_window_position(0, 0)
        path = website_path("editor.html")
        cls.editor_url = "file://%s" % path

    @classmethod
    def tearDownClass(cls):
        try:
            cls.driver.quit()
        except:
            pass

    def tearDown(self):
        super(BaseSeleniumTestCase, self).tearDown()

        # Confirm a existing alert dialog, otherwise followed test will failed
        # with selenium.common.exceptions.UnexpectedAlertPresentException
        try:
            alert = self.driver.switch_to.alert
            alert.accept() # Confirm a alert dialog, otherwise
        except NoAlertPresentException:
            pass

    def out(self, *args):
        print(*args, file=sys.stderr)

    def _verbose_assertion_error(self, driver):
        self.out("\n")
        self.out("*" * 79)
        traceback.print_exc()
        self.out(" -" * 40)

        page_source = driver.page_source

        if not page_source.strip():
            self.out("[page coure is empty!]")
        else:
            page_source = "\n".join([line for line in page_source.splitlines() if line.rstrip()])
            self.out(page_source)

        self.out("*" * 79)
        self.out("\n")
        raise

    def _get_console_text(self):
        console = self.driver.find_element_by_id("console")
        console_text = console.text
        return console_text.strip()

    def assertConsole(self, txt):
        console_text = self._get_console_text()
        
        txt = textwrap.dedent(txt).strip()
        msg = textwrap.dedent("""

            *** Console output is: ***
            %s

            *** the reference: ***
            %s

            *** diff: ***
            %s
        """) % (
            console_text, txt, make_diff(console_text, txt)
        )
        self.assertEqual(console_text, txt, msg=msg)


class EditorTests(BaseSeleniumTestCase):
    """
    Request and init PyPyJS in setUpClass
    and no complete reload before every tests
    """

    @classmethod
    def setUpClass(cls):
        super(EditorTests, cls).setUpClass()
        cls.driver.get(cls.editor_url)

        print("\nWait for init...", file=sys.stderr)
        assert "PyPy.js" == cls.driver.title

        check = WebDriverWait(cls.driver, 10).until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "console"), "Welcome to PyPy.js!"
            )
        )
        assert check

    def run_code(self, code):
        """
        paste the given code into CodeMirror editor and click on 'run' button
        here we don't do a WebDriverWait() call!
        """
        code=code.replace("\\", "\\\\")
        code=code.replace("'", "\\'")
        code2 = "\\n".join(textwrap.dedent(code).strip().splitlines())

        # remove #run_info text for safety catch the execution run end:
        self.driver.execute_script('$("#run_info").text("");')

        # self.out("\nExecute script: '%s'" % script)
        self.driver.execute_script("CodeMirrorEditor.setValue('%s');" % code2)
        # editor_code = self.driver.execute_script("return CodeMirrorEditor.getValue();")
        # self.out("from editor: %r" % editor_code)

        # execute by clicking on the #run button
        self.driver.find_element_by_id("run").click()

    def execute_editor(self, code, timeout=10):
        self.run_code(code)

        # Wait that #run_info is filled with e.g.: "Run in 123ms"
        try:
            check = WebDriverWait(self.driver, timeout).until(
                expected_conditions.text_to_be_present_in_element(
                    (By.ID, "run_info"), "Run in "
                )
            )
        except TimeoutException:
            msg=(
                "Timeout reached while execution of:\n"
                "-----------------------------------\n"
                "%s\n"
                "-----------------------------------\n"
                "Console output:\n"
                "-----------------------------------\n"
                "%s\n"
                "-----------------------------------\n"
            ) % (code, self._get_console_text())
            self.fail(msg=msg)
        else:
            self.assertTrue(check)

        run_info_element = self.driver.find_element_by_id("run_info")
        run_info = run_info_element.text
        # self.out("\n%s" % run_info)
        return run_info

    def assertEditor(self, code, output):
        run_info = self.execute_editor(code)
        self.assertConsole(output)
        self.assertIn("OK", run_info)
        self.assertNotIn("Error", run_info)

    def test_execute_editor(self, script=None):
        self.execute_editor("""
            print "Hello PyPy.js!"
        """)
        self.assertConsole("""
            Hello PyPy.js!
        """)
        console_text = self.driver.execute_script('return $("#console").text();')
        console_text = console_text.strip()
        self.assertEqual(console_text, "Hello PyPy.js!")

    def test_execute_escaping(self):
        self.assertEditor("""
            print 'single quote'
        """, """
            single quote
        """)
    
        self.assertEditor("""
            print "double quote"
        """, """
            double quote
        """)
    
        self.assertEditor("""
            print "a 'single quote' in double quote"
        """, """
            a 'single quote' in double quote
        """)
    
        self.assertEditor("""
            print 'a "double quote" in single quote'
        """, """
            a "double quote" in single quote
        """)
    
        self.assertEditor("""
            print "a\\nnew line"
        """, """
            a
            new line
        """)
    
        self.assertEditor("""
            print "OK\\nisn't it?"
        """, """
            OK
            isn't it?
        """)

    def test_execute_multiline(self):
        self.assertEditor("""
            print "one"
            print "two"
        """, """
            one
            two
        """)

        self.assertEditor("""
            for i in range(2):
                print i

            print "OK"
        """, """
            0
            1
            OK
        """)

    def test_standard_out_streams(self):
        self.assertEditor("""
            import sys
            sys.stdout.write("to sys.stdout\\n")
            sys.stderr.write("to sys.stderr\\n")
        """, """
            to sys.stdout
            to sys.stderr
        """)

    def test_sys_version(self):
        self.assertEditor("""
            import sys
            print sys.version
        """, """
            2.7.8 (?, May 17 2015, 07:02:41)
            [PyPy 2.5.0]
        """)

        self.assertEditor("""
            import sys
            for path in sys.path:
                print path
        ""","""
            /lib/pypyjs/lib_pypy/__extensions__
            /lib/pypyjs/lib_pypy
            /lib/pypyjs/lib-python/2.7
            /lib/pypyjs/lib-python/2.7/lib-tk
            /lib/pypyjs/lib-python/2.7/plat-linux2
        """)


    def test_sys_platform(self):
        """
        https://github.com/rfk/pypyjs/issues/49
        """
        self.assertEditor("""
            import sys
            print sys.platform
        """, """
            js
        """)

    def test_name(self):
        """
        https://github.com/rfk/pypyjs/issues/104
        vm._execute_source("print __name__") -> __builtin__
        vm.exec("print __name__") -> __main__
        """
        self.assertEditor("print __name__ ", "__main__")

    def test_pickle(self):
        """
        https://github.com/rfk/pypyjs/issues/83
        """
        self.assertEditor("""
            import cPickle as pickle
            d = pickle.dumps({'foo': 'bar'})
            print d
            print pickle.loads(d)
        """, """
            (dp1
            S'foo'
            p2
            S'bar'
            p3
            s.
            {'foo': 'bar'}
        """)
        self.assertEditor("""
            import pickle
            print pickle.loads(pickle.dumps({'a': 'a'}))
        """, """
            {'a': 'a'}
        """)

    def test_js_module1(self):
        self.assertEditor("""
            import js
            math = js.globals.Math
            print(math.log(2))
        """, """
            0.6931471805599453
        """)

    def test_js_module2(self):
        """
        https://github.com/rfk/pypyjs/issues/56
        """
        self.assertEditor("""
            import js
            js.eval('var one = 123.456')
            print js.eval('one')
        """, """
            123.456
        """)

    def test_js_alert(self):
        self.run_code("""
            import js
            js.eval("alert('hello world')")
            print "OK"
        """)
        alert_is_present = WebDriverWait(self.driver, timeout=5).until(
            expected_conditions.alert_is_present()
        )
        self.assertTrue(alert_is_present)

        alert = self.driver.switch_to.alert
        self.assertEqual(alert.text, "hello world")

    def test_js_decorator(self):
        self.assertEditor("""
            import js

            @js.Function
            def decorated():
                print "second"

            js.globals.setTimeout(decorated, 10)
            print "first"
        """, """
            first
            second
        """)

    def test_module_random(self):
        """
        https://github.com/rfk/pypyjs/issues/4
        """
        self.assertEditor("""
            import random
            print random.__file__
        """, """
            /lib/pypyjs/lib_pypy/random.py
        """)

    def test_module_pprint(self):
        """
        https://github.com/rfk/pypyjs/issues/5
        """
        self.assertEditor("""
            import pprint
            pprint.pprint({"foo":range(10), "bar":range(10,20)})
        """, """
            {'bar': [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
             'foo': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}
        """)

    def test_module_platform(self):
        """
        https://github.com/rfk/pypyjs/issues/6
        """
        self.assertEditor("""
            import platform
            print platform.__file__
        """, """
            /lib/pypyjs/lib_pypy/platform.py
        """)

    def test_module_os(self):
        self.assertEditor("""
            import os
            print os.__file__
        """, """
            /lib/pypyjs/lib_pypy/os.py
        """)

    def test_import(self):
        """
        test  __import__
        """
        self.assertEditor("""
            try:
                print sys.version
            except NameError:
                print "OK"
            sys = __import__('sys')
            print sys.platform
        """, """
            OK
            js
        """)

    def test_imports(self):

        # Request indirect the content of /website/js/pypy.js-0.3.0/lib/modules/index.json
        # startup a VM:
        self.execute_editor("print 'init done'")
        self.assertEqual(self._get_console_text(), "init done")

        # get 'vm._allModules'
        vm_all_modules = self.driver.execute_script("return vm._allModules")
        # self.out(pprint.pformat(vm_all_modules))

        # hack a list of available modules:
        libpath = website_path("js/pypy.js-0.3.0/lib/modules")
        module_names = [
            os.path.splitext(item)[0]
            for item in sorted(os.listdir(libpath))
            if not item.startswith("_") and item.endswith(".py")
        ]
        # module_names = ["sys", "random", "this"]
        total_count = len(module_names)

        # Check if all collected module_names exist in vm._allModules
        for module_name in module_names:
            self.assertIn(module_name, vm_all_modules)

        self.out("\nAll %i modules found in vm._allModules" % total_count)

        good = failed = 0
        self.out("\nTry to import modules:")
        for no, module_name in enumerate(sorted(module_names)):
            self.out("\n *** %s ***" % module_name)
            code = "import %s;print 'OK'" % module_name
            self.execute_editor(code)
            response = self._get_console_text()

            if module_name=="this":
                if response.startswith("The Zen of Python") and response.endswith("OK"):
                    response = "OK"

            if response=="OK":
                good += 1
            elif "Error" in response:
                failed += 1
            else:
                self.fail(msg=response)
            self.out("\t%i/%i: %s" % (no, total_count, response))

            if failed >= 10:
                self.fail("import test failed more than 10 times. Abort the test.")

        self.assertEqual(failed, 0,
            "Import %i modules: %i ok - %i failed" % (
                total_count, good, failed
            )
        )

    def test_namespace(self):
        self.assertEditor("""
            import sys
            print "locals:", locals()
            print "globals:", globals()
        """, """
            locals: {'__name__': '__main__', '__builtins__': <module '__builtin__' (built-in)>, '__package__': None, 'sys': <module 'sys' (built-in)>}
            globals: {'__name__': '__main__', '__builtins__': <module '__builtin__' (built-in)>, '__package__': None, 'sys': <module 'sys' (built-in)>}
        """)

        # We get a fresh PyPyJS(), so sys is not imported anymore:
        self.assertEditor("""
            print "locals:", locals()
            print "globals:", globals()
        """, """
            locals: {'__name__': '__main__', '__builtins__': <module '__builtin__' (built-in)>}
            globals: {'__name__': '__main__', '__builtins__': <module '__builtin__' (built-in)>}
        """)


if __name__ == "__main__":
    unittest.main(
        verbosity=3,
        # failfast=True,

        # run a specific test, e.g.:
        # argv=("test_editor", "EditorTests",)
        # argv=("test_editor", "EditorTests.test_imports",)
        # argv=("test_editor",
        #     "EditorTests.test_js_alert",
        #     "EditorTests.test_js_decorator",
        # )
    )