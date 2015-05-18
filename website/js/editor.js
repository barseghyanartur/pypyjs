jQuery( document ).ready(function( $ ) {
    $("#actions").submit(function() {
        // never "submit" the actions-form
        return false;
    })
    CodeMirrorEditor = CodeMirror.fromTextArea($("#editor")[0], {
        mode: {
            name: "text/x-cython",
            version: 2,
            singleLineStringErrors: false
        },
        lineNumbers: true,
        indentUnit: 4,
        matchBrackets: true
    });
    CodeMirrorEditor.on("changes", function() {
        // remove last run info after code changes.
        $("#run_info").text("");
    });
    $("#wrap_output").prop( "checked", false );
    $("#wrap_output").change(function() {
        if($(this).is(":checked")) {
            $(".jqconsole").css("word-wrap", "break-word");
            $(".jqconsole").css("white-space", "pre-wrap");
        } else {
            $(".jqconsole").css("word-wrap", "");
            $(".jqconsole").css("white-space", "");
        }
    });
});

function verbose_exec(vm, code, verbose=true) {
    $("#run_info").text("start vm...");
    jqconsole.Reset();
    // console.log("Start code:" + JSON.stringify(code));
    var start_time = new Date();
    vm.exec(code).then(function() {
        if (verbose) {
            var duration = new Date() - start_time;
            $("#run_info").text("Run in " + duration + "ms (OK)");
        }
    }, function (err) {
        // err is an instance of PyPyJS.Error
        if (verbose) {
            var duration = new Date() - start_time;
            $("#run_info").text("Run in " + human_time(duration) + " ("+err.name+": "+err.message+"!)");
        }
        vm.stderr(err.trace); // the human-readable traceback, as a string
    });
}

$(function () {
    var init_start = new Date();

    // Global vars, for easy debugging in console.
    window.jqconsole = $('#console').jqconsole('', '>>> ');
    window.vm = new PyPyJS();

    // Send all VM output to the console.
    vm.stdout = vm.stderr = function(data) {
        jqconsole.Write(data, 'jqconsole-output');
    }

    // Display a helpful message and twiddle thumbs as it loads.
    vm.stdout('Loading PyPy.js.\n')
    vm.stdout('It\'s big, so this might take a while...\n\n')
    vm.ready.then(function() {
        $("#loading").slideUp();
        $("#actions").slideDown("slow");

        verbose_exec(vm, 'print "Welcome to PyPy.js!"', verbose=false)
        var duration = new Date() - init_start;
        $("#run_info").text("PyPy.js init in " + human_time(duration));

        $("#run").click(function() {
            var code=CodeMirrorEditor.getValue();
            verbose_exec(vm, code);
        });
    }, function(err) {
        jqconsole.Write('ERROR: ' + err);
    });
});