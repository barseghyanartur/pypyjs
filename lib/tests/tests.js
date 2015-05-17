//
// A very minimal testsuite for the PyPy.js shell code.
// We should do something a lot nicer than this...
//

var PyPyJS;
if (typeof PyPyJS === 'undefined') {
  
  if (typeof require !== 'undefined') {
    PyPyJS = require('../pypy.js');
  } else if (typeof loadRelativeToScript !== 'undefined') {
    loadRelativeToScript('../pypy.js');
  } else if (typeof load !== 'undefined') {
    load('pypy.js');
  }
}

var log
if (typeof console !== 'undefined') {
  log = console.log.bind(console);
} else {
  log = print;
}

var vm = new PyPyJS();

var PyPyJSTestResult = vm.ready

// First, check that python-level errors will actually fail the tests.
.then(function() {
  return vm.exec("raise RuntimeError");
})
.then(function() {
  throw new Error("Python exception did not trigger js Error");
}, function(err) {
  if (! err instanceof PyPyJS.Error) {
    throw new Error("Python exception didn't trigger PyPyJS.Error instance");
  }
})

// Check that the basic set-eval-get cycle works correctly.
.then(function() {
  return vm.set("x", 7);
})
.then(function() {
  return vm.exec("x = x * 2");
})
.then(function() {
  return vm.get("x");
})
.then(function(x) {
  if (x !== 14) {
    throw new Error("set-eval-get cycle failed");
  }
})

// Check that we execute in correctly-__name__'d python scope.
.then(function() {
  return vm.exec("assert __name__ == '__main__', __name__")
})

// Check that sys.platform tells us something sensible.
.then(function() {
  return vm.exec("import sys; assert sys.platform == 'js'");
})

// Report success or failure at the end of the chain.
.then(function(res) {
  log("TESTS PASSED!");
}, function(err) {
  log("TESTS FAILED!");
  log(err);
  throw err;
});
