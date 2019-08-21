var rawBytes = btoa("{{ encoded }}");
var ROWS = Math.max(Math.ceil(rawBytes.length / 16), 1);
var BYTE_HEIGHT;
var ROW_OFFSET = 0;

function highlight(byte_id, length, css_class) {
    if(typeof length === 'undefined') {
        length = 1;
    }
    if(typeof css_class === 'undefined') {
        css_class = "highlighted";
    }
    byte_id = parseInt(byte_id);
    length = parseInt(length);
    $("." + css_class).removeClass(css_class);
    for(var i=0; i<length; ++i) {
        $(".byte[byteid=" + (byte_id + i) + "]").addClass(css_class);
    }
}

function cursor(byte_id) {
    highlight(byte_id, 1, "cursor");
}

function visibleRows() {
    return Math.floor($('.hexeditor .scrollcontainer').first().innerHeight() / BYTE_HEIGHT) - 2;
}

$(document).ready(function() {
    BYTE_HEIGHT = $('.hexeditor .byte').first().outerHeight();
    $(".scrollheightproxy").height(BYTE_HEIGHT * ROWS);
    console.log(BYTE_HEIGHT * ROWS);
    $(".hexeditor .scrollcontainer").scroll(function() {
        console.log("Scroll!");
    });
    $('.hexeditor .scrollcapture').bind('mousewheel', function(e){
        if(e.originalEvent.wheelDelta /120 > 0) {
            if(ROW_OFFSET > 0) {
                --ROW_OFFSET;
            }
        } else{
            if(ROW_OFFSET < ROWS - visibleRows() + 1) {
                ++ROW_OFFSET;
            }
        }
        e.preventDefault();
        $(".hexeditor .scrollcontainer").scrollTop(BYTE_HEIGHT * ROW_OFFSET);
    });
    $(".bytes .byte").css("cursor", "none").hover(function() {
        cursor($(this).attr('byteid'));
    })
    $(".hexdump .byte").css("cursor", "none").hover(function() {
        cursor($(this).attr('byteid'));
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
            $(".byte[byteid=" + (offset + i) + "]").addClass("manually-focused");
        }
        $(this).addClass("manually-focused");
    });
    $(".tree_label").mouseout(function() {
        $(".highlighted").removeClass("highlighted");
    });
});