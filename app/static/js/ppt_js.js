

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

        let gap = { small: 6, medium: 4, large: 2 }[_thumbnail_size];
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


// give a tracing for modal seleciton
$(document).ready(function () {
    $('.modal.bs-example-modal-lg').on('shown.bs.modal', function (event) {
        let currentmoal = parseInt($(event.target).attr('name'));
        $('img.active[data-toggle="modal"]').css('border', "").removeClass('active');
        $(`img[name="${currentmoal}"]`).css('border', "10px solid rgb(92, 236, 99)").css('box-sizing', 'border-box').addClass('active');
    })
})

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

var _thumbnail_size

function _set_thumbnail(event, size) {
    set_thumbnail(size)
    $(event.target).blur();
};
function set_thumbnail(size) {
    _thumbnail_size = size
    $('.thumbnail_small').removeClass('active');
    $('.thumbnail_medium').removeClass('active');
    $('.thumbnail_large').removeClass('active');
    switch (size) {
        case "small":
            //  $('.slide_image_container').addClass('slidezoom');
            $('.slide_input').addClass('thumbnail-hidden').css('display', 'none');
            $('.slide_container').removeClass("col-xs-3 col-xs-6").addClass(' col-xs-2 ');
            $('.box').removeClass('medium large').addClass('small');
            $('.thumbnail_small').addClass('active');
            $('slide_title').removeClass().addClass('slide_title small');
            $('.zoom-hidden-text').css('display', "");

            break;
        case 'medium':
            // $('.slide_image_container').addClass('slidezoom');
            $('.slide_input').removeClass('thumbnail-hidden').css('display', 'block');
            $('.slide_container').removeClass('col-xs-6 col-xs-2').addClass('col-xs-3 ');
            $('.box').removeClass('small large').addClass('medium');
            $('slide_title').removeClass('small large').addClass('medium');
            $('.thumbnail_medium').addClass('active');
            $('.zoom-hidden-text').css('display', 'block');

            break;
        case 'large':
            //  $('.slide_image_container').removeClass('slidezoom');
            $('.slide_input').removeClass('thumbnail-hidden').css('display', 'block');
            $('.box').removeClass("small medium").addClass('large');
            $('slide_title').removeClass("small medium").addClass('large');
            $('.slide_container').removeClass("col-xs-3 col-xs-2").addClass('col-xs-6');
            $('.thumbnail_large').addClass('active');
            $('.zoom-hidden-text').css('display', 'block');
            break;
    };
    /*for (let i = 0; i < divs.length; i += grid_col) {
     divs.slice(i, i + grid_col).wrapAll("<div class='row slide_row'> </div>  ")
   }*/
};

$(document).ready(set_thumbnail("small"))

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

$(function () {
    $("#sortable").sortable({ handle: '.slide_title' });
    $("#sortable").disableSelection();
});
