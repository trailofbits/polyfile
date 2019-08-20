var lastHighlight = null;
var lastHighlightLength = null;
var lastCursor = null;

function highlight(byte_id, length) {
    if(typeof length === 'undefined') {
        length = 1
    }
    byte_id = parseInt(byte_id);
    length = parseInt(length);
    if(lastHighlight !== null) {
        for(var i=0; i<lastHighlightLength; ++i) {
            $("#byte" + (lastHighlight + i)).removeClass("highlighted");
            $("#hexbyte" + (lastHighlight + i)).removeClass("highlighted");
        }
    }
    for(var i=0; i<length; ++i) {
        $("#byte" + (byte_id + i)).addClass("highlighted");
        $("#hexbyte" + (byte_id + i)).addClass("highlighted");
    }
    lastHighlight = byte_id;
    lastHighlightLength = length;
}

function cursor(byte_id) {
    byte_id = parseInt(byte_id);
    if(lastCursor !== null) {
        $("#byte" + lastCursor).removeClass("cursor");
        $("#hexbyte" + lastCursor).removeClass("cursor");
    }
    $("#byte" + byte_id).addClass("cursor");
    $("#hexbyte" + byte_id).addClass("cursor");
    lastCursor = byte_id;
}

$(document).ready(function() {
    $(".bytes .byte").css("cursor", "none").hover(function() {
        cursor($(this)[0].id.substring(4));
    })
    $(".hexdump .byte").css("cursor", "none").hover(function() {
        cursor($(this)[0].id.substring(7));
    })
    $(".tree_label").hover(function() {
        highlight($(this).attr('matchbyte'), $(this).attr('matchlength'));
    });
    $(".tree_label:not([for])").css("cursor", "zoom-in").click(function() {
        var hadFocus = $(this).hasClass("manually-focused");
        $(".manually-focused").removeClass("manually-focused");
        if(hadFocus) {
            return;
        }
        var offset = parseInt($(this).attr('matchbyte'));
        for(var i=0; i<parseInt($(this).attr('matchlength')); ++i) {
            $("#byte" + (offset + i)).addClass("manually-focused");
            $("#hexbyte" + (offset + i)).addClass("manually-focused");
        }
        $(this).addClass("manually-focused");
    });
    $(".tree_label").mouseout(function() {
        $(".highlighted").removeClass("highlighted");
    });
});