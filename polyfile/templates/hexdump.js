var rawBytes = atob("{{ encoded }}");
var ROWS = Math.max(Math.ceil(rawBytes.length / 16), 1);
var BYTE_HEIGHT;
var ROW_OFFSET = 0;
var VISIBLE_ROWS = 0;
var highlights = {};
var linesByRow = [1];
var LINE_DIGITS = 1;

function downloadFile() {
    download('data:{{ mime_type }};base64,'+ btoa(rawBytes), '{{ filename.replace("'", "\\'") }}', '{{ mime_type }}');
}

function assignLines() {
    var line = 1;
    for(var i=0; i<rawBytes.length; ++i) {
        if(rawBytes.charCodeAt(i) == 10) {
            ++line;
        }
        if(i % 16 == 15) {
            linesByRow.push(line);
        }
    }
    if(rawBytes % 16 != 15) {
        linesByRow.push(line);
    }
    LINE_DIGITS = Math.ceil(Math.log(linesByRow[linesByRow.length-1]) / Math.log(10));
}

function highlight(byte_id, length, css_class, remove_existing) {
    if(typeof length === 'undefined') {
        length = 1;
    }
    if(typeof css_class === 'undefined') {
        css_class = "highlighted";
    }
    if(typeof remove_existing === 'undefined') {
        remove_existing = true;
    }
    byte_id = parseInt(byte_id);
    length = parseInt(length);
    if(remove_existing) {
        removeHighlight(css_class);
    }
    if(!(css_class in highlights)) {
        highlights[css_class] = [];
    }
    for(var i=0; i<length; ++i) {
        highlights[css_class].push([-1, byte_id + i]);
    }
    updateHighlights(css_class);
}

function mouseOverByte(byte_id) {
    $('.tree_label').removeClass("highlighted");
    cursor(byte_id);
    $('.tree_label').filter(function() {
        var start = parseInt($(this).attr('matchbyte'));
        if(start > byte_id) {
            return false;
        }
        var length = parseInt($(this).attr('matchlength'));
        return byte_id < start + length;
    }).addClass('highlighted');
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
        $('#rbyte' + cell_id).removeClass(css_class);
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
                $('#rbyte' + cell_id).removeClass(css_class);
                highlights[css_class][i][0] = -1;
            }
        }

        if(current_cell_id >= 0 && current_cell_id < VISIBLE_ROWS * 16) {
            $("#byte" + current_cell_id).addClass(css_class);
            $("#ascii" + current_cell_id).addClass(css_class);
            $("#rbyte" + current_cell_id).addClass(css_class);
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

function updateRendering() {
    if(linesByRow.length <= ROW_OFFSET) {
        assignLines();
    }

    function newline(n) {
        return '<div class="byteline"><span class="byterow">'
            + n.toString(10).padStart(LINE_DIGITS, '0')
            + ':&nbsp;</span>';
    }

    var startOffset = ROW_OFFSET * 16;
    var line = linesByRow[ROW_OFFSET];
    var html = newline(line);

    for(var i=startOffset; i < startOffset + VISIBLE_ROWS * 16; ++i) {
        if(rawBytes.charCodeAt(i) == 10) {
            html += '<br />' + newline(++line);
        } else {
            html += '<span id="rbyte'
                + (i - startOffset)
                + '" onmouseover="mouseOverByte(' + i + ')">'
                + formatChar(rawBytes[i], false) + "</span>";
        }
    }

    $('.readablebytes').html(html).scrollTop(0);
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
    updateRendering();
    updateHighlights();
    $(".hexeditor .scrollcontainer").scrollTop(BYTE_HEIGHT * ROW_OFFSET);
}

function resizeWindow() {
    var newVisible = Math.max(1, Math.floor($('.hexeditor .scrollcontainer').first().innerHeight() / BYTE_HEIGHT) - 2);
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
                mouseOverByte(parseInt($(this)[0].id.substring(4)) + ROW_OFFSET * 16);
            });
            $("#ascii" + byte_id).css("cursor", "none").hover(function() {
                mouseOverByte(parseInt($(this)[0].id.substring(5)) + ROW_OFFSET * 16);
            });
        }
        ++VISIBLE_ROWS;
    }
    scrollToRow();
}

function clearSelection() {
    if(document.selection && document.selection.empty) {
        document.selection.empty();
    } else if(window.getSelection) {
        var sel = window.getSelection();
        sel.removeAllRanges();
    }
}

var searchMatches = [];
var currentMatch = 0;

function kmp_table(source) {
    var pos = 0;
    var cnd = 0;
    var t = [-1];

    while(++pos < source.length) {
        if(source.charCodeAt(pos) == source.charCodeAt(cnd)) {
            t.push(t[cnd]);
        } else {
            t.push(cnd);
            cnd = t[cnd];
            while(cnd >= 0 && source.charCodeAt(pos) != source.charCodeAt(cnd)) {
                cnd = t[cnd];
            }
        }
        ++cnd;
    }

    t[pos] = cnd;

    return t;
}

function kmp_search(source, find, caseSensitive) {
    if(!source) {
        return [];
    }
    if(!find) {
        return source.split('').map(function(_, i) { return i; });
    }
    if(typeof caseSensitive === 'undefined') {
        caseSensitive = false;
    }
    if(!caseSensitive) {
        source = source.toLowerCase();
        find = find.toLowerCase();
    }
    var t = kmp_table(find);
    var j = 0;
    var k = 0;
    var result = [];
    while(j < source.length) {
        if(find.charCodeAt(k) == source.charCodeAt(j)) {
            ++j;
            if(++k == find.length) {
                result.push(j - k);
                k = t[k];
            }
        } else {
            k = t[k];
            if(k < 0) {
                ++j;
                ++k;
            }
        }
    }
    return result;
}

var hexMatcher = new RegExp('^(0[xX])?([0-9a-fA-F]+)$');

function pageSearch() {
    searchMatches = [];
    currentMatch = 0;
    $('#searchinfo').text('');
    $('#searchbuttons').hide();
    removeHighlight('searchresult');
    var query = $('#search').val();
    if(query === null || query == "") {
        return;
    }

    for(var index of kmp_search(rawBytes, query)) {
        highlight(index, query.length, 'searchresult', false);
        searchMatches.push(index);
    }

    if(hexMatcher.test(query)) {
        /* also test for the byte sequence */
        var match = query;
        if(match.substring(0, 2).toLowerCase() == "0x") {
            match = match.substring(2);
        }
        var str = '';
        if(match.length % 2 == 1) {
            match = '0' + match;
        }
        for(var i=0; i<match.length; i+=2) {
            str += String.fromCharCode(parseInt(match[i] + match[i+1], 16))
        }
        for(var index of kmp_search(rawBytes, str, true)) {
            highlight(index, str.length, 'searchresult', false);
            searchMatches.push(index);
        }
    }

    if(searchMatches.length == 0) {
        $('#searchinfo').text('0/0');
        return;
    }

    if(searchMatches.length > 1) {
        $('#searchbuttons').show();
    }

    updateSearch();
}

function updateSearch() {
    $('#searchinfo').text((currentMatch + 1) + '/' + searchMatches.length);
    scrollToByte(searchMatches[currentMatch]);
}

function searchUp() {
    if(--currentMatch < 0) {
        currentMatch = searchMatches.length - 1;
    }
    updateSearch();
}

function searchDown() {
    if(++currentMatch >= searchMatches.length) {
        currentMatch = 0;
    }
    updateSearch();
}

var doubleClicked = false;

$(document).ready(function() {
    BYTE_HEIGHT = $('.hexeditor .byte').first().outerHeight();
    $(".scrollheightproxy").height(BYTE_HEIGHT * (ROWS + 2));
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
        $('.tree_label').removeClass('highlighted');
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

    $(window).keydown(function(e) {
        if ( ( e.keyCode == 70 && ( e.ctrlKey || e.metaKey ) ) ||
            ( e.keyCode == 191 ) ) {
            e.preventDefault();
            $('#search').focus().select();
        } else if ( e.keyCode == 71 && ( e.ctrlKey || e.metaKey ) ) {
            e.preventDefault();
            searchDown();
        }
        return true;
    });

    $(".byterow").css("cursor", "zoom-in").attr('title', 'Double-Click to Jump to Address').dblclick(function() {
        doubleClicked = true;
        clearSelection();
        var clickedRow = this;
        $(this).css('font-weight', 'bold').css('background-color', 'black').css('color', 'white');
        setTimeout(function() {
            /* use a timeout here to give the browser time to render the results of clearSelection() before the popup */
            var addr = prompt('To what address would you like to jump?', $(clickedRow).text());
            if(addr !== null) {
                $(clickedRow).css('font-weight', '').css('background-color', '').css('color', '');
                addr = parseInt(addr, 16);
                scrollToByte(addr);
                setTimeout(function() {
                    $('#byte' + (addr - ROW_OFFSET * 16))
                        .fadeOut("fast")
                        .css('font-weight', 'bold')
                        .fadeIn(3000);
                    setTimeout(function() {
                        $('#byte' + (addr - ROW_OFFSET * 16)).css('font-weight', 'normal');
                    }, 5000);
                }, 1000);
            } else {
                setTimeout(function() {
                    $(clickedRow).css('font-weight', '').css('background-color', '').css('color', '');
                }, 500);
            }
        }, 100);
    }).click(function() {
        doubleClicked = false;
        setTimeout(function() {
            if(!doubleClicked) {
                $('#clickinfo').fadeIn("slow", function() {
                    $('#clickinfo').delay(1000).fadeOut("slow");
                });
            }
        }, 1000);
    });
});