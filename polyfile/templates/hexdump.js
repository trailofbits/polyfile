var lastHighlight = null;

function highlight(byte_id) {
    console.log("highlight(" + byte_id + ")");
    if(lastHighlight !== null) {
        $("#byte" + lastHighlight).removeClass("highlighted");
        $("#hexbyte" + lastHighlight).removeClass("highlighted");
    }
    $("#byte" + byte_id).addClass("highlighted");
    $("#hexbyte" + byte_id).addClass("highlighted");
    lastHighlight = byte_id;
}

$(document).ready(function() {
    $(".bytes .byte").css("cursor", "none").hover(function() {
        highlight($(this)[0].id.substring(4));
    })
    $(".hexdump .byte").css("cursor", "none").hover(function() {
        highlight($(this)[0].id.substring(7));
    })
});