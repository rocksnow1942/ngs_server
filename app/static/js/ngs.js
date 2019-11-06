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

function set_bar_color(barid, progress) {
    let color = '';
    if (progress<=30) {color='progress-bar-success'} 
    else if (30<progress && progress<70) {color='progress-bar-warning'}
    else {color='progress-bar-danger'}
    $(jq_id(barid)).removeClass('progress-bar-success progress-bar-warning progress-bar-danger').addClass(color);
};