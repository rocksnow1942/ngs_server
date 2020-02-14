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


// replicate datafiles to a ngs_sample group. 
function replicateNGSSampleGroupDatafile(url,uploadto) {
   
    let target = prompt('Enter NGS Sample Group ID you want to copy data file from:');
    if (target) {
       fetch(url, {
           method: "POST",
           headers: { "content-type": "application/json" },
           body: JSON.stringify({ uploadto, target }),
       })
           .then(res => res.json())
           .then(result => {
               if (result.refresh) {
                   setTimeout(() => {
                       location.reload()
                   }, 1500);
               }
               display_flash_message(result.html, 1000)
                   ;
           })
           .catch(err => { console.log(err) })
   }
}