
// show hidden text, then chaning DOM window scroll. not using anymore. 
function show_hidden_title_body(event) {
    let status = $(event.target).text();
    let scroll = $(window).scrollTop();
    let element;
    let offset;
    $(".img-responsive").each(function () {

        if ($(this).offset().top - scroll > 100) {
            element = $(this);
            offset = $(this).offset().top - scroll;
            return false
        }

    });
    if (status == 'Show Text') {
        $(".thumbnail-hidden").css('display', 'block');
        $(event.target).text("Hide Text");
    }
    else {
        $(".thumbnail-hidden").css('display', 'none');
        $(event.target).text("Show Text");
    };
    $(window).scrollTop($(element).offset().top - offset);
};

// keyboard to move modal.
$(document).ready(function () {
    $(document).keydown(function (e) {

        let gap = { small: 6, medium: 4, large: 2,list:1 }[_thumbnail_size];
        let current_modal_id, current_div_index;
        if ($(`img.active[data-toggle='modal']`).length) {
            current_modal_id = $(`img.active[data-toggle='modal']`).attr('name');
            current_div_index = $(`img.active[data-toggle='modal']`).closest('.slide_container').index();
        }
        else {
            current_modal_id = 1;
            current_div_index = 0;
        }
        if (e.which == 32 && e.target.tagName == 'BODY') {  //space = 32
            $(`.modal[name="${current_modal_id}"]`).modal('show');
            e.preventDefault();
            e.stopPropagation();
            return
        }
        else if (e.which == 32 && $(e.target).attr('class') == "modal bs-example-modal-lg in") {
            $(`.modal[name="${current_modal_id}"]`).modal('hide');
            e.preventDefault();
            e.stopPropagation();
            return
        }
        let next_div_index = -100;

        switch (e.which) {
            case 37: // left
                next_div_index = current_div_index - 1;
                break;
            case 38: // up
                next_div_index = current_div_index - gap;
                break;
            case 39: // right
                next_div_index = current_div_index + 1;
                break;
            case 40: // down
                next_div_index = current_div_index + gap;
                break;
        }
        let nextmodal = $(`.slide_container:nth-of-type(${next_div_index + 1})`).find('img');
        if (nextmodal.length) {
            if ($(e.target).attr('class') == "modal bs-example-modal-lg in") {
                $(e.target).modal('hide');
                $(`.modal[name="${nextmodal.attr('name')}"]`).modal('show');
                e.preventDefault();
                e.stopPropagation();
            }
            else if (e.target.tagName == 'BODY') {
                $('img.active[data-toggle="modal"]').css('border', "").removeClass('active');
                nextmodal.css('border', "10px solid rgb(92, 236, 99)").css('box-sizing', 'border-box').addClass('active');
                e.preventDefault();
                e.stopPropagation();
            }
            let windowheight = $(window).height();
            if ($(`img[name="${nextmodal.attr('name')}"]`).offset().top - $(window).scrollTop() > windowheight - 45) {
                $(window).scrollTop($(`img[name="${nextmodal.attr('name')}"]`).offset().top - 15);
            }
            else if ($(`img[name="${nextmodal.attr('name')}"]`).offset().top - $(window).scrollTop() < 15) {
                $(window).scrollTop($(`img[name="${nextmodal.attr('name')}"]`).offset().top - windowheight + 50)
            }
        }
    })
});


// give a tracing for modal seleciton; once a modal is show, show boarder to other data toggle image.
$(document).ready(function () {
    $('.modal.bs-example-modal-lg').on('shown.bs.modal', function (event) {
        let currentmoal = parseInt($(event.target).attr('name'));
        $('img.active[data-toggle="modal"]').css('border', "").removeClass('active');
        $(`img[name="${currentmoal}"]`).css('border', "10px solid rgb(92, 236, 99)").css('box-sizing', 'border-box').addClass('active');
    })
})

// open tag and note eidtor for slides
$(".slide_edit_trigger").on('click', function (event) {
    let id = $(this).attr('id');
    if (!$(this).find('input').length) {
        let tag = $(this).find('span.slide_tag').text();
        let note = $(this).find('span.slide_note').text();
        tag = tag === 'None' ? "" : tag;
        note = note === 'None' ? "" : note;
        $(this).find("span.slide_tag").html(`
        <div class="input-group">
        <input type="text" class="form-control" value="${tag}" list='tags_list' >
            <span class="input-group-btn">
                <button class="btn btn-default" type="button" onclick="save_edit(event,'slide','tag','${id}')">Save Tag</button>
            </span>
                </div> `);
        $(this).find("span.slide_note").html(`<div class="input-group">
            <input type="text" class="form-control" value="${note}">
                <span class="input-group-btn">
                    <button class="btn btn-default" type="button" onclick="save_edit(event,'slide','note','${id}')">Save Note</button>
                </span>
                </div>`)
    }
});


// open tag and note eidtor for ppt 
$(".ppt_edit_trigger").on('click', function (event) {
    let id = $(this).attr('id');
    if (!$(this).find('input').length) {
        let note = $(this).find('span.ppt_note').text();
        note = note === 'None' ? "" : note;
        $(this).find("span.ppt_note").html(`<div class="input-group">
            <input type="text" class="form-control" value="${note}">
                <span class="input-group-btn">
                    <button class="btn btn-default" type="button" onclick="save_edit(event,'ppt','note','${id}')">Save Note</button>
                </span>
                </div>`)
    }
});

// open tag and note eidtor for project
$(".project_edit_trigger").on('click', function (event) {
    let id = $(this).attr('id');
    if (!$(this).find('input').length) {
        let note = $(this).find('span.project_note').text();
        note = note === 'None' ? "" : note;
        $(this).find("span.project_note").html(`<div class="input-group">
            <input type="text" class="form-control" value="${note}">
                <span class="input-group-btn">
                    <button class="btn btn-default" type="button" onclick="save_edit(event,'project','note','${id}')">Save Note</button>
                </span>
                </div>`)
    }
});


var _thumbnail_size

function _set_thumbnail(event, size,table) {
    if (size=='list' && ['project','ppt',].includes(table)) {
        $(event.target).blur();
    } else {
        set_thumbnail(size)
        $(event.target).blur();
    }
};

// change page layout for slide ppt and project layout.
function set_thumbnail(size) {
    _thumbnail_size = size
    $('[class^="thumbnail_"]').removeClass('active');
   /* $('.thumbnail_medium').removeClass('active');
    $('.thumbnail_large').removeClass('active');
    $('.thumbnail_large').removeClass('active');*/
    $('.slide_image_container').removeClass('col-xs-2');
    switch (size) {
        case "small":
            //  $('.slide_image_container').addClass('slidezoom');       
            $('.slide_input.outer').css('display', 'none');
            $('.thumbnail_title_text').css('display', 'block');
            $('.slide_container').removeClass("col-xs-3 col-xs-6 col-xs-12").addClass(' col-xs-2 ');
            // $('.box').removeClass('medium large').addClass('small');
            $('.thumbnail_small').addClass('active');
            $('.slide_title.outer').removeClass('medium large').addClass('small');
            $('.zoom-hidden-text').css('display', "");
            $('.thumbnail_list_text').css('display', 'none');

            break;
        case 'medium':
            // $('.slide_image_container').addClass('slidezoom');
           
            $('.slide_input.outer').css('display', 'block');
            $('.slide_container').removeClass('col-xs-6 col-xs-2 col-xs-12').addClass('col-xs-3 ');
            // $('.box').removeClass('small large').addClass('medium');
            $('.slide_title.outer').removeClass('small large').addClass('medium');
            $('.thumbnail_medium').addClass('active');
            $('.zoom-hidden-text').css('display', 'block');
            $('.thumbnail_list_text').css('display', 'none');

            break;
        case 'large':
            //  $('.slide_image_container').removeClass('slidezoom');
           
            $('.thumbnail_title_text').css('display', 'block');
            $('.slide_input.outer').css('display', 'block');
            $('.box').removeClass("small medium").addClass('large');
            // $('.slide_title.outer').removeClass("small medium").addClass('large');
            $('.slide_container').removeClass("col-xs-3 col-xs-2 col-xs-12").addClass('col-xs-6');
            $('.thumbnail_large').addClass('active');
            $('.zoom-hidden-text').css('display', 'block');
            $('.thumbnail_list_text').css('display', 'none');
            break;
        case 'list':
            $('.slide_image_container').addClass('col-xs-2');
            $('.slide_input.outer').css('display', 'none');
            $('.slide_container').removeClass("col-xs-3 col-xs-2 col-xs-6").addClass('col-xs-12');
            // $('.box').removeClass("small medium large");
            $('.thumbnail_title_text').css('display','none');
            $('.thumbnail_list_text').css('display', 'block');
            $('.thumbnail_list').addClass('active');
            $('.zoom-hidden-text').css('display', 'none');
            break;
        
    };
    set_box_height(_thumbnail_size)
    
};

// add sortable to slides. 
$(function () {
    $("#sortable").sortable({ handle: '.slide_title' });
    $("#sortable").disableSelection();
});

function set_box_height (size) {
    let boxwidth = $(".box").width();
    let extra = { 'list': 0, 'small': 89, 'medium': 137, 'large': 137 }[size];
    // let height = { 'list': 'auto', 'small': boxwidth * 1, 'medium': boxwidth * 1, 'large': boxwidth * 1}[size];
    let height = extra + boxwidth*0.75;
    if (size=='list') {
        $(".box").css('min-height', boxwidth / 6);
    };
    $(".box").height(height);
}

$(document).ready(function () {
    $(window).resize(function () {
     set_box_height(_thumbnail_size);   
    });
});
