var rawBytes = atob("{{ encoded }}");
var ROWS = Math.max(Math.ceil(rawBytes.length / 16), 1);
var BYTE_HEIGHT;
var ROW_OFFSET = 0;
var VISIBLE_ROWS = 0;
var highlights = {};

function highlight(byte_id, length, css_class) {
    if(typeof length === 'undefined') {
        length = 1;
    }
    if(typeof css_class === 'undefined') {
        css_class = "highlighted";
    }
    byte_id = parseInt(byte_id);
    length = parseInt(length);
    removeHighlight(css_class);
    if(!(css_class in highlights)) {
        highlights[css_class] = [];
    }
    for(var i=0; i<length; ++i) {
        highlights[css_class].push([-1, byte_id + i]);
    }
    updateHighlights(css_class);
}

function removeHighlight(css_class) {
    if(!(css_class in highlights)) {
        return;
    }
    for(var i=0; i<highlights[css_class].length; ++i) {
        var cell_id = highlights[css_class][i][0];
        var byte_id = highlights[css_class][i][1];
        $('#byte' + cell_id).removeClass(css_class);
        $('#ascii' + cell_id).removeClass(css_class);
    }
    highlights[css_class] = [];
}

function updateHighlights(css_class) {
    if(typeof css_class === 'undefined') {
        /* update all types */
        for(var css_class in highlights) {
            updateHighlights(css_class);
        }
        return;
    } else if(!(css_class in highlights)) {
        return;
    }
    var offset = ROW_OFFSET * 16;
    for(var i=0; i<highlights[css_class].length; ++i) {
        var cell_id = highlights[css_class][i][0];
        var byte_id = highlights[css_class][i][1];

        var current_cell_id = byte_id - offset;

        if(current_cell_id != cell_id) {
            if(cell_id >= 0) {
                $('#byte' + cell_id).removeClass(css_class);
                $('#ascii' + cell_id).removeClass(css_class);
                highlights[css_class][i][0] = -1;
            }
        }

        if(current_cell_id >= 0 && current_cell_id < VISIBLE_ROWS * 16) {
            $("#byte" + current_cell_id).addClass(css_class);
            $("#ascii" + current_cell_id).addClass(css_class);
            highlights[css_class][i][0] = current_cell_id;
        }
    }
}

function cursor(byte_id) {
    highlight(byte_id, 1, "cursor");
}

function scrollToByte(byte_id) {
    scrollToRow(Math.floor(byte_id / 16));
}

function formatChar(c, monospace) {
    if(typeof monospace === 'undefined') {
        monospace = true;
    }
    if(typeof c === 'undefined' || c.length == 0 || c == ' ') {
        return '&nbsp;';
    } else if(c == '\n') {
        if(monospace) {
            return '\u2424';
        } else {
            '\u2424</span><br /><span>';
        }
    } else if(c == '\t') {
        if(monospace) {
            return '\u2b7e';
        } else {
            return '\t';
        }
    } else if(c == '\r') {
        return '\u240d';
    }
    return c.replace('>', '&gt;').replace('<', '&lt;');
}

function scrollToRow(row) {
    if(typeof row === 'undefined') {
        row = ROW_OFFSET;
    }
    if(row < 0 || ROWS <= VISIBLE_ROWS) {
        row = 0;
    } else if(row > ROWS - VISIBLE_ROWS) {
        row = ROWS - VISIBLE_ROWS;
    }
    ROW_OFFSET = row;
    var startOffset = ROW_OFFSET * 16;
    for(var i=startOffset; i < startOffset + VISIBLE_ROWS * 16; ++i) {
        var bytecode;
        var bytestring;
        if(i >= rawBytes.length) {
            bytecode = '';
            bytestring = '';
        } else {
            bytecode = rawBytes.charCodeAt(i).toString(16).padStart(2, '0');
            bytestring = formatChar(rawBytes[i]);
        }
        $("#byte" + (i - startOffset)).text(bytecode);
        $("#ascii" + (i - startOffset)).html(bytestring);
    }
    /* update the row labels */
    var requiredDigits = Math.ceil(Math.log(rawBytes.length) / Math.log(16));
    for(var i=0; i<VISIBLE_ROWS; ++i) {
        $("#byterow" + i).text(((i + ROW_OFFSET) * 16).toString(16).padStart(requiredDigits, '0'));
    }
    updateHighlights();
    $(".hexeditor .scrollcontainer").scrollTop(BYTE_HEIGHT * ROW_OFFSET);
}

function resizeWindow() {
    var newVisible = Math.floor($('.hexeditor .scrollcontainer').first().innerHeight() / BYTE_HEIGHT) - 2;
    while(VISIBLE_ROWS < newVisible) {
        /* add a new row */
        var rowHtml = '<div class="byteline"><span class="byterow" id="byterow' + VISIBLE_ROWS + '"></span>';
        var offset = VISIBLE_ROWS * 16;
        for(var i=0; i<16; ++i) {
            rowHtml += '<span class="byte" id="byte' + (offset + i) + '"></span>';
        }
        rowHtml += "</div>";
        $('.hexdump').append(rowHtml);
        /* now make the ASCII rows: */
        rowHtml = '<div class="byteline">';
        for(var i=0; i<16; ++i) {
           rowHtml += '<span class="byte" id="ascii' + (offset + i) + '"></span>';
        }
        rowHtml += "</div>";
        $('.bytes').append(rowHtml);
        /* add the event listeners: */
        for(var i=0; i<16; ++i) {
            var byte_id = offset + i;
            $("#byte" + byte_id).css("cursor", "none").hover(function() {
                highlight(parseInt($(this)[0].id.substring(4)) + ROW_OFFSET * 16, 1, "cursor");
            });
            $("#ascii" + byte_id).css("cursor", "none").hover(function() {
                highlight(parseInt($(this)[0].id.substring(5)) + ROW_OFFSET * 16, 1, "cursor");
            });
        }
        ++VISIBLE_ROWS;
    }
    scrollToRow();
}

$(document).ready(function() {
    BYTE_HEIGHT = $('.hexeditor .byte').first().outerHeight();
    $(".scrollheightproxy").height(BYTE_HEIGHT * ROWS);
    $(window).resize(resizeWindow());
    resizeWindow();
    $('#loading').remove();
    $(".hexeditor .scrollcontainer").scroll(function() {
        scrollToRow(Math.floor($(this).scrollTop() / BYTE_HEIGHT));
    });
    $('.hexeditor .scrollcapture').bind('mousewheel', function(e){
        if(e.originalEvent.wheelDelta /120 > 0) {
            if(ROW_OFFSET > 0) {
                --ROW_OFFSET;
            }
        } else{
            if(ROW_OFFSET < ROWS - VISIBLE_ROWS) {
                ++ROW_OFFSET;
            }
        }
        e.preventDefault();
        scrollToRow();
    }).on("mouseleave", function() {
        /* have the cursor disappear when our mouse leaves the hex dump */
        removeHighlight('cursor');
        updateHighlights('cursor');
    });;
//    $(".bytes .byte").css("cursor", "none").hover(function() {
//        cursor($(this).attr('byteid'));
//    })
//    $(".hexdump .byte").css("cursor", "none").hover(function() {
//        cursor($(this).attr('byteid'));
//    })
    $(".tree_label").hover(function() {
        highlight($(this).attr('matchbyte'), $(this).attr('matchlength'));
    });
    $(".tree_label:not([for])").css("cursor", "zoom-in").click(function() {
        if($(this).hasClass("manually-focused")) {
            removeHighlight("manually-focused");
            $(this).removeClass("manually-focused");
            return;
        }
        $(".manually-focused").removeClass("manually-focused");
        var offset = parseInt($(this).attr('matchbyte'));
        var length = parseInt($(this).attr('matchlength'));
        highlight(offset, length, "manually-focused");
        $(this).addClass("manually-focused");
        scrollToByte(offset);
    });
    $(".tree_label").mouseout(function() {
        $(".highlighted").removeClass("highlighted");
    });
});