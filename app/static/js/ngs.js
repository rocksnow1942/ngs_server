// jquery legal id names
function jq_id(myid) {
    return "#" + myid.replace(/(:|\.|\[|\]|,|=|@)/g, "\\$1");
}


// update progressbar
function set_bar_progress(barid, progress) {
    const p = progress + '%';
    const txt = ((progress == 100) ? 'Done.' : p);
    $(jq_id(barid)).css('width', p).attr('aria-valuenow', progress).text(txt);
};

