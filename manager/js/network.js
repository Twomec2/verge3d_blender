window.removeS3Files = function() {
    var checkers = document.getElementsByClassName('netcheckbox');

    var deleteKeys = [];

    for (var i = 0; i < checkers.length; i++) {
        var checker = checkers[i];

        if (checker.checked)
            deleteKeys.push(checker.value);
    }

    var url = '/storage/net/?req=delete&key=' + deleteKeys.join('&key=');

    makeRequest(url, null, function(response) {
        var dia = appendDialog(response);
        openDialog(dia);
    });
}

window.toggleDir = function(checkerDir) {
    var checkers = document.querySelectorAll('.netcheckbox, .netcheckboxdir')

    for (var i = 0; i < checkers.length; i++) {
        var checker = checkers[i];

        if (checker.value.indexOf(checkerDir.value) > -1)
            checker.checked = checkerDir.checked;
    }
}
