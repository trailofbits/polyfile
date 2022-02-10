const rawBytes = atob("{{ encoded }}");
const ROWS = Math.max(Math.ceil(rawBytes.length / 16), 1);
let BYTE_HEIGHT;
let ROW_OFFSET = 0;
let VISIBLE_ROWS = 0;
let highlights = {};
let linesByRow = [1];
let LINE_DIGITS = 1;
let $bytes = [];
let $ascii = [];
let $rbytes = [];

function getByte(index) {
    if(index < $bytes.length && index >= 0) {
        return $bytes[index];
    } else {
        return $("#byte" + index)
    }
}

function getAscii(index) {
    if(index < $ascii.length) {
        return $ascii[index];
    } else {
        return $("#ascii" + index);
    }
}

const mime_types = {
    "text/html": "html",
    "text/css": "css",
    "text/xml": "xml",
    "image/gif": "gif",
    "image/jpeg": "jpg",
    "application/x-javascript": "js",
    "application/atom+xml": "atom",
    "application/rss+xml": "rss",
    "text/mathml": "mml",
    "text/plain": "txt",
    "text/vnd.sun.j2me.app-descriptor": "jad",
    "text/vnd.wap.wml": "wml",
    "text/x-component": "htc",
    "image/png": "png",
    "image/tiff": "tif",
    "image/vnd.wap.wbmp": "wbmp",
    "image/x-icon": "ico",
    "image/x-jng": "jng",
    "image/x-ms-bmp": "bmp",
    "image/svg+xml": "svg",
    "image/webp": "webp",
    "application/java-archive": "jar",
    "application/mac-binhex40": "hqx",
    "application/msword": "doc",
    "application/pdf": "pdf",
    "application/postscript": "ps",
    "application/rtf": "rtf",
    "application/vnd.ms-excel": "xls",
    "application/vnd.ms-powerpoint": "ppt",
    "application/vnd.wap.wmlc": "wmlc",
    "application/vnd.google-earth.kml+xml": "kml",
    "application/vnd.google-earth.kmz": "kmz",
    "application/x-7z-compressed": "7z",
    "application/x-cocoa": "cco",
    "application/x-java-archive-diff": "jardiff",
    "application/x-java-jnlp-file": "jnlp",
    "application/x-makeself": "run",
    "application/x-perl": "pl",
    "application/x-pilot": "prc",
    "application/x-rar-compressed": "rar",
    "application/x-redhat-package-manager": "rpm",
    "application/x-sea": "sea",
    "application/x-shockwave-flash": "swf",
    "application/x-stuffit": "sit",
    "application/x-tcl": "tcl",
    "application/x-x509-ca-cert": "pem",
    "application/x-xpinstall": "xpi",
    "application/xhtml+xml": "xhtml",
    "application/zip": "zip",
    "application/octet-stream": "bin",
    "audio/midi": "mid",
    "audio/mpeg": "mp3",
    "audio/ogg": "ogg",
    "audio/x-realaudio": "ra",
    "video/3gpp": "3gpp",
    "video/mpeg": "mpg",
    "video/quicktime": "mov",
    "video/x-flv": "flv",
    "video/x-mng": "mng",
    "video/x-ms-asf": "asx",
    "video/x-ms-wmv": "wmv",
    "video/x-msvideo": "avi",
    "video/mp4": "mp4",
};

function downloadFile(offset, length, mime_type, extension) {
    if(typeof offset === 'undefined') {
        offset = 0;
    }
    if(typeof length === 'undefined') {
        length = rawBytes.length;
    }
    if(typeof mime_type === 'undefined' || !mime_type) {
        if(typeof extension !== 'undefined' && extension) {
            for(const [mime, ext] of Object.entries(mime_types)) {
                if(ext === extension) {
                    mime_type = mime;
                    break;
                }
            }
        }
        if(typeof mime_type === 'undefined' || !mime_type) {
            if(offset === 0 && length === rawBytes.length) {
                mime_type = '{{ mime_type }}';
            } else {
                mime_type = 'application/octet-stream';
            }
        }
    }
    if(typeof extension === 'undefined' || !extension) {
        if(mime_type in mime_types) {
            extension = mime_types[mime_type];
        }
    }
    let filename = '{{ filename.replace("'", "\\'") }}';
    if(offset !== 0 || length !== rawBytes.length || mime_type !== '{{ mime_type }}') {
        filename += "@" + offset + "-" + (offset + length - 1);
        if(typeof extension !== 'undefined' && extension) {
            filename += "." + extension;
        }
    }
    download('data:{{ mime_type }};base64,'+ btoa(rawBytes.slice(offset, offset + length)),
        filename, mime_type);
}

function assignLines() {
    let line = 1;
    for(let i=0; i<rawBytes.length; ++i) {
        if(rawBytes.charCodeAt(i) === 10) {
            ++line;
        }
        if(i % 16 === 15) {
            linesByRow.push(line);
        }
    }
    if(rawBytes.length % 16 !== 15) {
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

class CacheNode {
    constructor(key, value, prev = null, next = null) {
        this.key = key;
        this.value = value;
        this.next = next;
        this.prev = prev;
    }
}

class LRUCache {
    constructor(limit = 1024, default_value = undefined) {
        this.size = 0;
        this.limit = limit;
        this.head = null;
        this.tail = null;
        this.cache = {};
        this.default_value = default_value;
    }

    clear() {
        this.size = 0;
        this.head = null;
        this.tail = null;
        this.cache = {};
    }

    detach(node) {
        if(node.prev !== null) {
            node.prev.next = node.next;
        } else {
            this.head = node.next;
        }
        if(node.next !== null) {
            node.next.prev = node.prev;
        } else {
            this.tail = node.prev;
        }
    }

    write(key, value) {
        const existing = this.cache[key];
        if(existing) {
          this.detach(existing);
          --this.size;
        } else {
            while(this.size >= this.limit) {
                delete this.cache[this.tail.key];
                this.detach(this.tail);
                --this.size;
            }
        }

        if(!this.head) {
            this.head = this.tail = new CacheNode(key, value);
        } else {
            const node = new CacheNode(key, value, this.head);
            this.head.prev = node;
            this.head = node;
        }
        this.cache[key] = this.head;
        ++this.size;
        return value;
    }

    contains(key) {
        return this.cache[key];
    }

    read(key) {
        const existing = this.cache[key];
        if(existing) {
            const value = existing.value;
            if(this.head !== existing) {
                this.write(key, value);
            }
            return value;
        }
        return this.default_value;
    }
}

let $byteLabelCache = new LRUCache(1024, $());

function labelsForByte(byte_id) {
    if($byteLabelCache.contains(byte_id)) {
        return $byteLabelCache.read(byte_id)
    } else {
        return $byteLabelCache.write(byte_id, $labels.filter(function() {
            const start = parseInt($(this).attr('matchbyte'));
            if(start > byte_id) {
                return false;
            }
            const length = parseInt($(this).attr('matchlength'));
            return byte_id < start + length;
        }));
    }
}

function mouseOverByte(byte_id) {
    $labels.removeClass("highlighted");
    cursor(byte_id);
    labelsForByte(byte_id).addClass("highlighted");
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

let lastScrollTime;

async function fillByteLabelCache() {
    const startScrollTime = lastScrollTime;
    for(let byte_id = 0; byte_id < VISIBLE_ROWS * 16; ++byte_id) {
        if(startScrollTime !== lastScrollTime) {
            break;
        }
        labelsForByte(byte_id); // cache the labels for this byte_id
        await sleep(1);
    }
}

function removeHighlight(css_class) {
    if(!(css_class in highlights)) {
        return;
    }
    for(let i=0; i<highlights[css_class].length; ++i) {
        const cell_id = highlights[css_class][i][0];
        if(cell_id < 0) {
            continue;
        }
        // const byte_id = highlights[css_class][i][1];
        getByte(cell_id).removeClass(css_class);
        getAscii(cell_id).removeClass(css_class);
        $('#rbyte' + cell_id).removeClass(css_class);
    }
    highlights[css_class] = [];
}

function updateHighlights(css_class) {
    if(typeof css_class === 'undefined') {
        /* update all types */
        for(let css_class in highlights) {
            updateHighlights(css_class);
        }
        return;
    } else if(!(css_class in highlights)) {
        return;
    }
    const offset = ROW_OFFSET * 16;
    for(let i=0; i<highlights[css_class].length; ++i) {
        const cell_id = highlights[css_class][i][0];
        const byte_id = highlights[css_class][i][1];

        const current_cell_id = byte_id - offset;

        if(current_cell_id !== cell_id) {
            if(cell_id >= 0) {
                getByte(cell_id).removeClass(css_class);
                getAscii(cell_id).removeClass(css_class);
                $('#rbyte' + cell_id).removeClass(css_class);
                highlights[css_class][i][0] = -1;
            }
        }

        if(current_cell_id >= 0 && current_cell_id < VISIBLE_ROWS * 16) {
            getByte(current_cell_id).addClass(css_class);
            getAscii(current_cell_id).addClass(css_class);
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
    if (typeof monospace === 'undefined') {
        monospace = true;
    }
    if (typeof c === 'undefined' || c.length === 0 || c === ' ') {
        return '&nbsp;';
    } else if (c === '\n') {
        if (monospace) {
            return '\u240A';
        } else {
            return '\u240A</span><br /><span>';
        }
    } else if (c === '\t') {
        if (monospace) {
            return '\u2b7e';
        } else {
            return '\t';
        }
    } else if (c.charCodeAt(0) < 32) {
        return String.fromCharCode(0x2400 + c.charCodeAt(0));
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

    const startOffset = ROW_OFFSET * 16;
    let line = linesByRow[ROW_OFFSET];
    let html = newline(line);

    for(let i=startOffset; i < startOffset + VISIBLE_ROWS * 16; ++i) {
        if(rawBytes.charCodeAt(i) === 10) {
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
    lastScrollTime = Date.now();
    if(typeof row === 'undefined') {
        row = ROW_OFFSET;
    }
    if(row < 0 || ROWS <= VISIBLE_ROWS) {
        row = 0;
    } else if(row > ROWS - VISIBLE_ROWS) {
        row = ROWS - VISIBLE_ROWS;
    }
    $byteLabelCache.clear();
    ROW_OFFSET = row;
    const startOffset = ROW_OFFSET * 16;
    for(let i=startOffset; i < startOffset + VISIBLE_ROWS * 16; ++i) {
        let bytecode;
        let bytestring;
        if(i >= rawBytes.length) {
            bytecode = '';
            bytestring = '';
        } else {
            bytecode = rawBytes.charCodeAt(i).toString(16).padStart(2, '0');
            bytestring = formatChar(rawBytes[i]);
        }
        getByte(i - startOffset).text(bytecode);
        getAscii(i - startOffset).html(bytestring);
    }
    /* update the row labels */
    const requiredDigits = Math.ceil(Math.log(rawBytes.length) / Math.log(16));
    for(let i=0; i<VISIBLE_ROWS; ++i) {
        $("#byterow" + i).text(((i + ROW_OFFSET) * 16).toString(16).padStart(requiredDigits, '0'));
    }
    updateRendering();
    updateHighlights();
    $(".hexeditor .scrollcontainer").scrollTop(BYTE_HEIGHT * ROW_OFFSET);
    fillByteLabelCache().then(() => {});
}

function resizeWindow() {
    const newVisible = Math.max(1, Math.floor($('.hexeditor .scrollcontainer').first().innerHeight() / BYTE_HEIGHT) - 2);
    while(VISIBLE_ROWS < newVisible) {
        /* add a new row */
        let rowHtml = '<div class="byteline"><span class="byterow" id="byterow' + VISIBLE_ROWS + '"></span>';
        const offset = VISIBLE_ROWS * 16;
        for(let i=0; i<16; ++i) {
            rowHtml += '<span class="byte" id="byte' + (offset + i) + '"></span>';
        }
        rowHtml += "</div>";
        $('.hexdump').append(rowHtml);
        /* now make the ASCII rows: */
        rowHtml = '<div class="byteline">';
        for(let i=0; i<16; ++i) {
           rowHtml += '<span class="byte" id="ascii' + (offset + i) + '"></span>';
        }
        rowHtml += "</div>";
        $('.bytes').append(rowHtml);
        /* add the event listeners: */
        for(let i=0; i<16; ++i) {
            const byte_id = offset + i;
            $("#byte" + byte_id).css("cursor", "none").hover(function() {
                mouseOverByte(parseInt($(this)[0].id.substring(4)) + ROW_OFFSET * 16);
            });
            $("#ascii" + byte_id).css("cursor", "none").hover(function() {
                mouseOverByte(parseInt($(this)[0].id.substring(5)) + ROW_OFFSET * 16);
            });
        }
        ++VISIBLE_ROWS;
    }
    $ascii = new Array(VISIBLE_ROWS * 16);
    $bytes = new Array(VISIBLE_ROWS * 16);
    $(".byte").each(function(b) {
        const result = $(this);
        const id = result[0].id;
        if(id.startsWith("byte")) {
            const idNumber = parseInt(id.substring(4), 10);
            $bytes[idNumber] = result;
        } else if(id.startsWith("ascii")) {
            const idNumber = parseInt(id.substring(5), 10);
            $ascii[idNumber] = result;
        }
    });
    scrollToRow();
}

function clearSelection() {
    if(document.selection && document.selection.empty) {
        document.selection.empty();
    } else if(window.getSelection) {
        const sel = window.getSelection();
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
        if(source.charCodeAt(pos) === source.charCodeAt(cnd)) {
            t.push(t[cnd]);
        } else {
            t.push(cnd);
            cnd = t[cnd];
            while(cnd >= 0 && source.charCodeAt(pos) !== source.charCodeAt(cnd)) {
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
    const t = kmp_table(find);
    let j = 0;
    let k = 0;
    var result = [];
    while(j < source.length) {
        if(find.charCodeAt(k) === source.charCodeAt(j)) {
            ++j;
            if(++k === find.length) {
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

const hexMatcher = new RegExp('^(0[xX])?([0-9a-fA-F]+)$');

let $labels;

function pageSearch() {
    searchMatches = [];
    currentMatch = 0;
    $('#searchinfo').text('');
    $('#searchbuttons').hide();
    removeHighlight('searchresult');
    $labels.removeClass('searchresult');
    const query = $('#search').val();
    if(query === null || query === "") {
        return;
    }

    const queryLower = query.toLowerCase();
    searchMatches = new Set($.map($labels, function(label) {
        if($(label).text().toLowerCase().includes(queryLower)) {
            const offset = $(label).attr('matchbyte');
            const length = $(label).attr('matchlength');
            highlight(offset, length, 'searchresult', false);
            $(label).addClass('searchresult');
            return offset;
        }
        return null;
    }).filter(result => result != null));

    for(let index of kmp_search(rawBytes, query)) {
        highlight(index, query.length, 'searchresult', false);
        searchMatches.add(index);
    }

    if(hexMatcher.test(query)) {
        /* also test for the byte sequence */
        let match = query;
        if(match.substring(0, 2).toLowerCase() === "0x") {
            match = match.substring(2);
        }
        let str = '';
        if(match.length % 2 === 1) {
            match = '0' + match;
        }
        for(let i=0; i<match.length; i+=2) {
            str += String.fromCharCode(parseInt(match[i] + match[i+1], 16))
        }
        for(let index of kmp_search(rawBytes, str, true)) {
            highlight(index, str.length, 'searchresult', false);
            searchMatches.add(index);
        }
    }

    if(searchMatches.size === 0) {
        $('#searchinfo').text('0/0');
        return;
    }

    searchMatches = Array.from(searchMatches).sort();

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

let doubleClicked = false;

$(document).ready(function() {
    BYTE_HEIGHT = $('.hexeditor .byte').first().outerHeight();
    $(".scrollheightproxy").height(BYTE_HEIGHT * (ROWS + 2));
    $(window).resize(resizeWindow);
    $labels = $('.tree_label');
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
        $labels.removeClass('highlighted');
        removeHighlight('cursor');
        updateHighlights('cursor');
    });
//    $(".bytes .byte").css("cursor", "none").hover(function() {
//        cursor($(this).attr('byteid'));
//    })
//    $(".hexdump .byte").css("cursor", "none").hover(function() {
//        cursor($(this).attr('byteid'));
//    })
    $labels.hover(function() {
        highlight($(this).attr('matchbyte'), $(this).attr('matchlength'));
    });
    $(".tree_label:not([for])").css("cursor", "zoom-in").click(function() {
        if($(this).hasClass("manually-focused")) {
            removeHighlight("manually-focused");
            $(this).removeClass("manually-focused");
            return;
        }
        $(".manually-focused").removeClass("manually-focused");
        const offset = parseInt($(this).attr('matchbyte'));
        const length = parseInt($(this).attr('matchlength'));
        highlight(offset, length, "manually-focused");
        $(this).addClass("manually-focused");
        scrollToByte(offset);
    });
    $labels.mouseout(function() {
        $(".highlighted").removeClass("highlighted");
    });

    $(window).keydown(function(e) {
        if ( ( e.keyCode === 70 && ( e.ctrlKey || e.metaKey ) ) ||
            ( e.keyCode === 191 ) ) {
            e.preventDefault();
            $('#search').focus().select();
        } else if ( e.keyCode === 71 && ( e.ctrlKey || e.metaKey ) ) {
            e.preventDefault();
            searchDown();
        } else if (("key" in e && (e.key === "Escape" || e.key === "Esc")) || e.keyCode === 27) {
            $(".manually-focused").removeClass("manually-focused");
            removeHighlight("manually-focused");
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
                    getByte(addr - ROW_OFFSET * 16)
                        .fadeOut("fast")
                        .css('font-weight', 'bold')
                        .fadeIn(3000);
                    setTimeout(function() {
                        getByte(addr - ROW_OFFSET * 16).css('font-weight', 'normal');
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
