// PPT_js .js


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

        let gap = { small: 6, medium: 4, large: 2, list: 1 }[_thumbnail_size];
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

function _set_thumbnail(event, size, table) {
    if (size == 'list' && ['project', 'ppt',].includes(table)) {
        $(event.target).blur();
    } else {
        set_thumbnail(size);
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
            // $('.slide_title.outer').removeClass('medium large').addClass('small');
            $('.zoom-hidden-text').css('display', "");
            $('.thumbnail_list_text').css('display', 'none');

            break;
        case 'medium':
            // $('.slide_image_container').addClass('slidezoom');

            $('.slide_input.outer').css('display', 'block');
            $('.slide_container').removeClass('col-xs-6 col-xs-2 col-xs-12').addClass('col-xs-3 ');
            // $('.box').removeClass('small large').addClass('medium');
            // $('.slide_title.outer').removeClass('small large').addClass('medium');
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
            $('.thumbnail_title_text').css('display', 'none');
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

function set_box_height(size) {
    let boxwidth = $(".box").width();
    let para = { 'list': 0, 'small': 89, 'medium': 137, 'large': 137 };
    let extra = para[size];

    // let height = { 'list': 'auto', 'small': boxwidth * 1, 'medium': boxwidth * 1, 'large': boxwidth * 1}[size];
    let height = Math.ceil(extra + boxwidth * 0.75);

    if (size == 'list') {
        $(".box").css('min-height', $('.slide_image_container').height());
        $(".box").height('auto');
    } else {
        $(".box").height(height);
    }
}

$(document).ready(function () {
    $(window).resize(function () {
        set_box_height(_thumbnail_size);
    });
});



// base.js 
// change nav bar active status based on url.
$(document).ready(function () {
    var url = window.location.pathname.split('/')[1];
    let perfectmatch = $('ul.nav a').filter(function () {
        return $(this).attr('href') == window.location.pathname;
    });
    if (perfectmatch.length) {
        perfectmatch.parent().addClass('active')
    } else {
        if (url) {
            $('ul.nav a[href*="' + url + '/"]').filter(function () { return $(this).attr('name') != 'badge_icon' }).parent().addClass('active');
        }
    }
});

// resize main container height to make bottom banner not too close to top.
$(document).ready(function () {
    $(window).resize(function () {
        var bodyheight = $(this).height();
        $("#main_container").css('min-height', bodyheight - 150);
    }).resize();
});



// display and close toast messages automatically if toast is not yellow.
function display_flash_message(result, time) {
    time = time ? time : 500;
    $(".flash_message_container").html(result);
    let toast = $(".my_toast_container").slideDown('slow', 'swing');
    if (!result.includes('toast--yellow')) {
        toast.delay(time).slideUp(500, 'swing')
    }
};

// function to close toast message. not in use.
function close_toast_message(time) {
    time = time ? time : 500;
    $(".my_toast_container").slideDown('slow', 'swing').delay(time).slideUp(500, 'swing')
}

// display toast message whenever a page reloads.
$(document).ready(function () {
    let category = [];
    $(".my_toast_container").each(function () { category.push($(this).attr('name')) });
    if (category.every((e) => { return e == 'success' | e == 'info' })) {
        $(".my_toast_container").slideDown('slow', 'swing').delay(1000).slideUp(500, 'swing')
    } else (
        $(".my_toast_container").slideDown('slow', 'swing')
    )
}); 



// ngs.js 

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
    if (progress <= 30) { color = 'progress-bar-success' }
    else if (30 < progress && progress < 70) { color = 'progress-bar-warning' }
    else { color = 'progress-bar-danger' }
    $(jq_id(barid)).removeClass('progress-bar-success progress-bar-warning progress-bar-danger').addClass(color);
};

// admin template js 
$(document).ready(function () {
    setInterval(function () {
        $.ajax({
            url: "{{ url_for('admin.get_system_usage')}}",
            type: "POST",
            success: function (result) {
                set_bar_progress('cpu_status', result.cpu);
                set_bar_progress('memory_status', result.memory);
                set_bar_color('cpu_status', result.cpu);
                set_bar_color('memory_status', result.memory)
            },
        });
    }, 1000)
})

$(document).ready(function () {
    $.ajax({
        url: "{{ url_for('admin.get_harddrive_usage')}}",
        type: "POST",
        success: function (result) {
            $('#harddrive_status').css('width', result.disk + '%').attr('aria-valuenow', result.disk).text(result.diskusage);
            $('#database_status').css('width', result.database + '%').attr('aria-valuenow', result.database).text(result.dbusage);
            set_bar_color('harddrive_status', result.disk);
            set_bar_color('database_status', result.database)
        },
    });
}
)

// draw bargraph for visting history using d3js
$(document).ready(function () {
    $.ajax({
        url: "{{ url_for('admin.get_access_log')}}",
        type: "POST",
        success: function (result) {
            draw_line(result)
        },
    });
}
)

function draw_line(data) {

    // set the dimensions and margins of the graph
    var margin = { top: 5, right: 10, bottom: 20, left: 32 },
        width = 320 - margin.left - margin.right,
        height = 100 - margin.top - margin.bottom;


    var x = d3.scale.ordinal().rangeRoundBands([0, width], .05);

    var y = d3.scale.linear().range([height, 0]);

    var xAxis = d3.svg.axis()
        .scale(x)
        .orient("bottom")
        ;

    var yAxis = d3.svg.axis()
        .scale(y)
        .tickFormat(d3.format(".1s"))
        .orient("left")
        .ticks(5)
        ;

    var svg = d3.select("#visit_history_line").append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform",
            "translate(" + margin.left + "," + margin.top + ")");

    // format the data

    data.forEach(function (d) {
        d.time = (d.time);
        d.value = +d.value;
    });

    x.domain(data.map(function (d) { return d.time; }));
    y.domain([0, d3.max(data, function (d) { return d.value; })]);

    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis)
        .selectAll("text")
        .style("text-anchor", "end")
        .attr("dx", "-.8em")
        .attr("dy", "-.55em")
        .attr("transform", "rotate(-90)")
        ;


    svg.append("g")
        .attr("class", "y axis")
        .call(yAxis)
        .append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", 6)
        .attr("dy", ".71em")
        .style("text-anchor", "end")
        .text("Visits");

    svg.selectAll("bar")
        .data(data)
        .enter().append("rect")
        .style("fill", "steelblue")
        .attr("x", function (d) { return x(d.time); })
        .attr("width", x.rangeBand())
        .attr("y", function (d) { return y(d.value); })
        .attr("height", function (d) { return height - y(d.value); });

};


// animal data display js 

// add tooltip
$(function () { $("[data-toggle='animal_help_tooltip']").tooltip() })


function toggle_image_scroll(event) {
    function scroll(e) {
        var scrollTo = null;
        if (e.type == 'mousewheel') {
            scrollTo = (e.originalEvent.wheelDelta * -1);
        }
        else if (e.type == 'DOMMouseScroll') {
            scrollTo = 40 * e.originalEvent.detail;
        }

        if (scrollTo) {
            e.preventDefault();
            $(this).scrollTop(scrollTo + $(this).scrollTop());
        }
    };
    let noscroll = $(event.target).closest('.btn').hasClass('btn-default');
    if (noscroll) {
        $('.figure_container').css({ 'overflow-y': 'scroll', 'max-height': $(window).height() });
        $(event.target).closest('.btn').attr('class', 'btn btn-danger');
        $('.figure_container').bind('mousewheel DOMMouseScroll', scroll)
    } else {
        $('.figure_container').css({ 'overflow-y': '', 'max-height': '' });
        $(event.target).closest('.btn').attr('class', 'btn btn-default')
        $('.figure_container').unbind('mousewheel DOMMouseScroll')
    }
}

$(function () {
    $(".sortable").sortable();
    $(".sortable").disableSelection();
});

// reset columns
function reset_columns(event) {
    let col = $(event.target).text();
    $('.columns_selector').attr('class', 'btn btn-default columns_selector');
    $(event.target).attr('class', 'btn btn-primary columns_selector');

    let colclass = `col-xs-${12 / col}` + ' columns';
    for (let i = 6; i > col; i--) {
        $(`.columns:nth-of-type(${i})`).css('display', 'none');
    };
    for (let i = 1; i <= col; i++) {
        $(`.columns:nth-of-type(${i})`).attr('class', colclass);
        $(`.columns:nth-of-type(${i})`).css('display', 'block');
    }
}

// select data form changes
$(document).on('change', '.animal_data_form', function (event) {
    let target = $(event.target).attr('name');
    if (target == 'note') { return };
    let form = $(event.target).closest('.form');
    let data = form.serializeArray();
    let col = form.attr('id');
    $.ajax({
        url: "{{url_for('apps.animal_data_form')}}",
        type: 'POST',
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (result) {
            if (result.form) {
                form.html(result.form);
                $(`#panel-title-${col[col.length - 1]}`).text(result.title);
                $("#figure-" + col[col.length - 1]).html("")
            }
        }
    })
})


// fetch and display images 
function display_figures(event, col) {
    // $(event.target).blur();
    let data = $('#form-' + col).serializeArray();
    $.ajax({
        url: "{{url_for('apps.animal_data_figure')}}",
        type: 'POST',
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (result) {
            if (result.html) {
                $("#figure-" + col).html(result.html);
                $('#form-' + col).find('input[name="note"]').val(result.note);
                $(".sortable").sortable();
                $(".sortable").disableSelection();
                figure_box_trigger_event();
            }
        }
    })
}

// save experiment data 
function save_experiment(event, col) {
    //  $(event.target).blur();
    let data = $('#form-' + col).serializeArray();
    let order = [];
    $(`#figure-${col}`).children().each(function () { order.push($(this).attr('name')) });
    $.ajax({
        url: "{{url_for('apps.save_animal_data')}}",
        type: 'POST',
        data: JSON.stringify({ data: data, order: order }),
        contentType: "application/json",
        success: function (result) {
            display_flash_message(result.html, 1000)
        }
    })
}

// change figure_box to active by click 
function click_active(event) {
    let target = $(event.target).parent().hasClass('active');
    $('.figure_box.active').removeClass('active');
    if (target) {
        return
    } else { $(event.target).parent().addClass('active').trigger('becomeActive') }
}

// figure_box class change will trigger an event, that will dynamically change the modal figure.
function figure_box_trigger_event() {
    $('.figure_box').on('becomeActive', function () {
        $('#animal_figure_modal_container').children().replaceWith($(this).children().clone())
    })
}

// keyboard to move figures // useful for move elements around, trigger element 
$(document).ready(function () {
    $(document).keydown(function (event) {
        if (!$('.figure_box.active').length) { return }
        else {
            // console.log(event.which) //32 space
            let current = $('.figure_box.active');
            let current_index = current.index();
            let left = current.parent().parent().prev().find(`.figure_box:nth-of-type(${current_index + 1})`);
            let right = current.parent().parent().next().find(`.figure_box:nth-of-type(${current_index + 1})`);
            if (event.target.tagName == 'BODY' && [32, 37, 39, 83, 38, 87, 40, 84, 66, 82].includes(event.which)) {
                event.preventDefault();
                let windowheight = $(window).height();
                let oldoffset = $(".figure_box.active").offset().top - $(window).scrollTop();
                switch (event.which) {
                    case 32: // space
                        // $('#animal_figure_modal').css('display','block')
                        $('#animal_figure_modal').modal('toggle')
                        break
                    case 37: // left
                        if (left.length) {
                            left.addClass('active').trigger('becomeActive')
                            current.removeClass('active')
                        }
                        break
                    case 39: //right
                        if (right.length && right.parent().parent().css('display') != 'none') {
                            right.addClass('active').trigger('becomeActive')
                            current.removeClass('active')
                        }
                        break
                    case 38: // up
                        if (current.prev().length) {
                            current.prev().addClass('active').trigger('becomeActive')
                            current.removeClass('active')
                        }
                        break
                    case 40: //down
                        if (current.next().length) {
                            current.next().addClass('active').trigger('becomeActive')
                            current.removeClass('active')
                        }
                        break
                    case 87: //  'w' 
                        current.insertBefore(current.prev())
                        break
                    case 83: //  s
                        current.insertAfter(current.next())
                        break
                    case 66: //  "b" key
                        current.parent().append(current);
                        current.removeClass('active');
                        current.parent().find(`.figure_box:nth-of-type(${current_index + 1})`).addClass('active').trigger('becomeActive');
                        break
                    case 84: //'t' key 
                        current.parent().prepend(current)
                        current.removeClass('active');
                        current.parent().find(`.figure_box:nth-of-type(${current_index + 1})`).addClass('active').trigger('becomeActive');
                        break
                    case 82: //'r' key 
                        current.parent().html(current.parent().children().sort(function (a, b) {
                            let ima = $(a).children().attr('alt');
                            let imb = $(b).children().attr('alt');
                            return ima < imb ? -1 : 1;
                        }))
                        current.parent().children().on('becomeActive', function () {
                            $('#animal_figure_modal_container').children().replaceWith($(this).children().clone())
                        })
                        break
                }
                // scroll to current active if scrolling up down 

                if ([38, 40, 82].includes(event.which)) {
                    if ($(".figure_box.active").offset().top - $(window).scrollTop() > windowheight - 45) {
                        $(window).scrollTop($(".figure_box.active").offset().top - 15);
                    }
                    else if ($(".figure_box.active").offset().top - $(window).scrollTop() < 15) {
                        $(window).scrollTop($(".figure_box.active").offset().top - windowheight + 50)
                    }
                } else if ([87, 83].includes(event.which)) {
                    $(window).scrollTop($(".figure_box.active").offset().top - oldoffset)
                }
            }
        }
    })
})



// calculate molecular weight 

$(document).on("change", "#sequence", function (event) {
    let seq = $(event.target).val().split(' ').join('').split('\n').join('').toUpperCase();
    let nt_weight = { 'A': 331.19748, 'T': 308.15758, 'C': 307.17278, 'G': 347.19628, 'Z': 179.151422, 'B': 405.444582 }; // m.w. of 2'f NMP-H2O
    let mw = 0;
    Object.keys(nt_weight).forEach(function (key) {
        let reg = new RegExp(key, 'g');
        mw += (seq.match(reg) || []).length * nt_weight[key]
    });
    mw -= 61.971762 // + H2O - HPO3
    $('#result').text(`M.W.: ${mw.toFixed(3)}`)
})


// load bokeh element and give it some time. 
$(document).ready(function () {
    let count = 0;
    let result = false;
    var interval = setInterval(function () {
        count += 1;
        $("#embeded_bokeh").children().each(function () {
            let id = $(this).attr('class');
            if (id || count >= 10) {
                if (id) { result = true; console.log('id loaded') };

                let count2 = 0;
                var interval2 = setInterval(function () {
                    count2 += 1;

                    if ($("input[placeholder='username']").attr('list') == 'usernamelist' || count2 >= 20) {
                        console.log('namelist attached.')
                        clearInterval(interval2);
                    }
                    $("input[placeholder='username']").attr('list', 'usernamelist');

                }, 200
                );

                clearInterval(interval);
            }
        })
    }, 200
    );
    setTimeout(function () {
        if (!result) {
            console.log(result);
            if (!result) {
                $("#embeded_bokeh").html(
                    `<h1>Load Application Failed ! &#128565;</h1>
                <img src="{{url_for('static',filename='images/loadfailed.gif')}}" class="img-responsive" alt="Responsive image">`)
            }
        };
    }, 3000);
}
)


// ngs 
// dynamically load knownas sequence
$(document).on("change", '#knownas', function (event) {
    let knownasname = event.target.value;
    let eventid = event.target.id
    $.ajax({
        url: "{{ url_for('ngs.get_known_as_sequence')}}",
        type: "POST",
        data: { knownas: knownasname },
        success: function (result) {

            $("#ks_sequence").val(result.sequence);

        },
        error: function (xhr, resp, text) {
            alert(`get_known_as_sequence Error: ${text}`)
        }
    });
    event.preventDefault();
});

//dynamically adjust round options based on selection value
$(document).on("change", '#selection', function (event) {
    let selectionname = event.target.value;
    $.ajax({
        url: "{{ url_for('ngs.get_selection_round')}}",
        type: "POST",
        data: { selection: selectionname },
        success: function (result) {
            let options = '';
            for (let round of result.rounds) {
                options += '<option value="' + round.name + '"></option>';
            };
            $("#rounds").html(options);

        },
        error: function (xhr, resp, text) {
            console.log(xhr, resp, text);
        }
    });
    event.preventDefault();
});

// remove entry from analysis cart. 
$(".glyphicon-trash").on("click", function (event) {
    $.ajax({
        url: "{{url_for('ngs.add_to_analysis')}}",
        type: "POST",
        data: JSON.stringify({ data: ['delete', event.target.id] }),
        contentType: 'application/json',
        success: function (result) {
            set_analysis_count_badge(result);
            let eles = $("tr[id*='round']");
            let remain = result['remaining'];
            for (let ele of eles) {
                if (!remain.includes(parseInt(ele.id.slice(6)))) {
                    $(ele).fadeOut(100);
                }
            };
        },
        error: function (xhr, resp, text) {
            console.log(xhr, resp, text);
        }
    })
});

// analysis page 
// set active tab
function set_active_tab(name) {
    $("div[role='tabpanel']").each(function (index) {
        let thisid = $(this).attr('id')
        if (thisid == name) {
            $(this).addClass('active in');
            $(`a[href='#${thisid}']`).parent().addClass('active');
        }
        else {
            $(this).removeClass('active in');
            $(`a[href='#${thisid}']`).parent().removeClass('active');
        };
    });
};


$(".glyphicon-trash").on("click", function (event) {
    let rowid = '#round_' + event.target.id;
    $(rowid).fadeOut();
    $(rowid).attr('id', 'trash' + event.target.id);
});

$("#save_edit").on('click', function save_edit() {
    if (confirm('Save Edit to Current Analysis?')) {
        let name = $("#name").val();
        let note = $("#note").val();
        let round = $("tr[id*='round']").toArray().map((ele) => { return ele.id });
        $.ajax({
            url: "{{url_for('ngs.edit_analysis')}}",
            type: "POST",
            data: JSON.stringify({ id: {{ analysis.id }}, name: name, note: note, round: round}),
    contentType: "application/json",
        success: function(result) {
            alert(result)
        },
error: function (xhr, resp, text) {
    console.log(xhr, resp, text);
}
        })}
    });

function replace_with_progressbar(id, result) {
    $(id).html(
        `<div class="progress ">
                <div class="progress-bar progress-bar-striped active" id="task:`+ result.id + `" role="progressbar"
                    aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" style="width:0%;">
                    0%
             </div>
            </div>`)
}

$('#load_rounds').on('click', function load_rounds() {
    if (confirm('Load selected rounds data to analysis?')) {
        $.ajax({
            url: "{{url_for('ngs.load_analysis_rounds')}}",
            type: "POST",
            data: JSON.stringify({ id: "{{ analysis.id }}"}),
    contentType: "application/json",
        }).done(function (result) {
        replace_with_progressbar("#load_progress", result);
        update_progress_bar();
    })    
        }        
    });


$('#start_cluster').on('click', function () {
    let distance = $('#distance').val();
    let cutoff_l = $('#cutoff_l').val();
    let cutoff_u = $('#cutoff_u').val();
    let threshold = $('#threshold').val();
    if (confirm('Start clustring with provided parameters?')) {
        $.ajax({
            url: "{{url_for('ngs.build_cluster')}}",
            type: "POST",
            data: JSON.stringify({ id: "{{ analysis.id }}", distance: distance, cutoff_l: cutoff_l, cutoff_u: cutoff_u, threshold: threshold}),
    contentType: "application/json",
        }).done(function (result) {
        if (result.id) {
            replace_with_progressbar("#cluster_progress", result);
            update_progress_bar();
        }
        else { alert('Wrong Parameters\n' + result.error) };
    })    
        }        
    });

function update_progress_bar() {
    let interval = setInterval(function () {
        var barlist = [];
        $('.progress-bar').each(function () {
            barlist.push(this.id);
        });
        // make ajax request to get  progress info
        $.ajax({
            url: "{{ url_for('ngs.get_bar_progress')}}",
            type: "POST",
            data: JSON.stringify({ barlist: barlist }),
            contentType: 'application/json',
            success: function (result) {
                let alldone = true;
                for (let [barid, progress] of Object.entries(result)) {
                    set_bar_progress(barid, progress);
                    if (progress < 100) { alldone = false };
                };
                // break out set interval if all done.
                if (alldone) { clearInterval(interval); window.location.reload() };
            },
            error: function (xhr, resp, text) {
                console.log(xhr, resp, text);
            }
        });
    }, 500);
};


// making progressbar when page first load.
$(document).ready(function () {
    if ($(".progress-bar").length) {
        update_progress_bar();
    };
});

// set badge count
function set_analysis_count_badge(result) {
    $('#analysis_cart_count').html(result['analysis_count']);
    $('#analysis_cart_count_container').css('display', result['analysis_count'] ? 'block' : 'none');
}


// change synthesis status.
function add_sequence_to_synthesis(id) {
    $.ajax({
        url: "{{url_for('ngs.add_sequence_to_synthesis')}}",
        type: "POST",
        data: JSON.stringify({ id: id }),
        contentType: 'application/json',
        success: function (result) {
            display_flash_message(result.html, 1000);
            let status = result.status;
            if (status == 'To Synthesis') {
                $('#add_sequence_to_synthesis' + id).html('Synthesized');
                $('#sequence_syn_status' + id).css('display', "").html(result.note);
            } else if (status == 'Synthesized') {
                $('#add_sequence_to_synthesis' + id).html('To Synthesis');
                $('#sequence_syn_status' + id).css('display', "").html(result.note)
            }
        }
    })
}


// ajax to add seleciton or round and update cart information.
function add_to_analysis(table, id) {
    $.ajax({
        url: "{{ url_for('ngs.add_to_analysis')}}",
        type: "POST",
        data: JSON.stringify({ data: [table, id] }),
        contentType: 'application/json',
        success: function (result) {
            // update cart rendering.
            set_analysis_count_badge(result);
        },
        error: function (xhr, resp, text) {
            console.log(xhr, resp, text);
        }
    });
}


function start_ngs_data_parsing(id, commit, ) {
    //let threshold = $(`#commit_threshold_${id}`).val() || 2;
    let filters = $('form#ngs_form_' + id).serializeArray()

    /*if ( isNaN(threshold) && (commit!='retract')) {
      alert('Enther a valid threshold, must be integer.')
      return
    };*/
    $.ajax({
        url: "{{url_for('ngs.ngs_data_processing')}}",
        type: "POST",
        data: JSON.stringify({ id: id, commit: commit, filters: filters }), //parseInt(threshold)
        contentType: 'application/json',
        success: function (result) {
            if (result.reload) { location.reload(); };
            display_flash_message(result.html, 1000);
        }
    })
};

// collect page information and generate csv file for download.
function download_sequence() {
    // let sequence_id = [];
    let current_page = $('span').filter(function () { return $(this).css('text-decoration').includes('underline'); }).text();
    let table_rows = [];
    $('tr').each(function () {
        let id = $(this).attr('id'); //&& id.startsWith('sequence_round_')
        if (id) {
            let row = [];
            //sequence_id.push(id.replace('sequence_round_(', '').split(',')[0]);
            // let sequence = $(this).find('b').html();
            row.push($(this).find('.entry_id').text().trim());
            $(this).find('.display_content').find('li').each(function () { row.push($(this).text().trim().replace(/,/g, " ")) });
            table_rows.push(row);
        };
    });

    let csvContent = "data:text/csv;charset=utf-8,"
        + table_rows.map(e => e.join(",")).join("\n");

    var encodedUri = encodeURI(csvContent);
    var link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", current_page + ".csv");
    document.body.appendChild(link); // Required for FF
    link.click();
}

$(document).ready($(".question_tooltip").each(function () { $(this).tooltip() }))


// display tree
function display_tree(id) {
    if ($('#tree-outer-container').css('display') == 'none') {
        $.ajax({
            url: "{{url_for('ngs.get_selection_tree_json')}}",
            type: "POST",
            data: JSON.stringify({ id: id }),
            contentType: 'application/json',
            success: function (result) {
                $('#tree-outer-container').css('display', 'block');
                draw_d3_tree(result.tree);
                $('#tree-container').addClass('row').attr('align', 'center');
            }
        })
    }
};
// save tree
function save_tree() {
    if (general_tree_data) {
        $.ajax({
            url: "{{url_for('ngs.save_tree')}}",
            type: "POST",
            data: JSON.stringify({ tree: general_tree_data }),
            contentType: 'application/json',
            success: function (result) {
                alert(result.msg[0].toUpperCase() + '!\n' + result.msg[1])
                //display_flash_message(result.html, 1000);
            },
        })
    }
}


// add extra sample member by clicking the button
$("#add-ngs-sample-member").on('click', function (event) {
    $.ajax({
        url: "{{ url_for('ngs.add_extrasample') }}",
        type: "POST",
        //dataType : 'json', // data type
        data: $("#add-ngs-sample-form").serialize(),
        success: function (result) {
            $("#add-ngs-sample-samples").html(result);
        },
        error: function (xhr, resp, text) {
            console.log(xhr, resp, text);
        }
    });
    event.preventDefault();
});
// delete certain member of the sample
$(document).on("click", '.add-ngs-sample-delete', function (event) {
    var todelete = event.target.id;
    if (confirm('Are you sure you want to delete item ' + todelete.toString() + " ?")) {
        $.ajax({
            url: "{{ url_for('ngs.delete_sample')}}" + "?todelete=" + todelete.toString(),
            type: "POST",
            data: $("#add-ngs-sample-form").serialize(),
            success: function (result) {
                $("#add-ngs-sample-samples").html(result);
            },
            error: function (xhr, resp, text) {
                console.log(xhr, resp, text);
            }
        });
    } else {
        // Do nothing!
    }
    ;
    event.preventDefault();
});

// add ngs sample page dynamicly change round options.
$(document).on("change", '.add-ngs-sample-column-1', function (event) {
    let selectionname = event.target.value;
    let eventid = event.target.id
    let roundcolid = eventid.replace('selection', 'round_id')
    $.ajax({
        url: "{{ url_for('ngs.get_selection_round')}}",
        type: "POST",
        data: { selection: selectionname },
        success: function (result) {

            let options = '';
            for (let round of result.rounds) {
                options += '<option value="' + round.id + '">' + round.name + '</option>';
            };
            $("#" + roundcolid).html(options);

        },
        error: function (xhr, resp, text) {
            console.log(xhr, resp, text);
        }
    });
    event.preventDefault();
});


// making progressbar when page first load.
$(document).ready(function () {
    if ($(".progress-bar").length) {
        update_progress_bar();
    };
});

function update_progress_bar() {
    let interval = setInterval(function () {
        var barlist = [];
        $('.progress-bar').each(function () {
            barlist.push(this.id);
        });

        // make ajax request to get  progress info
        $.ajax({
            url: "{{ url_for('ngs.get_bar_progress')}}",
            type: "POST",
            data: JSON.stringify({ barlist: barlist }),
            contentType: 'application/json',
            success: function (result) {
                let alldone = true;
                for (let [barid, progress] of Object.entries(result)) {

                    set_bar_progress(barid, progress);
                    if (progress < 100) { alldone = false };
                };
                // break out set interval if all done.
                if (alldone) {
                    clearInterval(interval);
                    $('#progress_title').html("<h1>Search Done. Redirecting ...</h1>");
                    let redirurl = "{{url_for('ngs.lev_search',table=table,task_id=task_id,**request.args)}}".split('&amp;').join('&');
                    setTimeout(() => { location.href = redirurl }, 1500)
                };
            },
            error: function (xhr, resp, text) {
                console.log(xhr, resp, text);
            }
        });
    }, 500);
};


// set page layout based on thumbain parameter
$(document).ready(set_thumbnail("{{thumbnail}}"));

// function add_ppt_to_follow is defined on base page.

// add flag RGB to slide; also for adding or deleting slide from collectoins (follow ppt, slide cart, bookmark)
function slide_add_flag(event, mode) {
    let slide_id = $(event.target).attr('name');
    let color = $(event.target).text();
    if ('NRGB'.split("").includes(color)) {
        // change and display flag
        let color_id = { N: "none", G: 'green', B: 'blue', R: 'red' }[color];
        let target_box = $(`span[name='${slide_id}']`).closest('.box');
        target_box.removeClass('red green blue').addClass(color_id);
        $.ajax({
            url: "{{url_for('ppt.add_flag')}}",
            type: "POST",
            data: JSON.stringify({ flag: color_id, slide_id: slide_id }),
            contentType: "application/json",
            success: function (result) {
                display_flash_message(result.html, 1000);
            },
            error: function (xhr, resp, text) { alert(`Error ppt.add_flag: ${text}`) },
        })
    } else {
        let action = $(event.target).parent().find('.glyphicon-minus').length ? 'delete' : 'add';
        // add to compare cart
        //console.log({ slide_id: slide_id, action: action, mode: mode });
        $.ajax({
            url: "{{ url_for('ppt.add_to_slide_cart')}}",
            type: "POST",
            data: JSON.stringify({ slide_id: slide_id, action: action, mode: mode }),
            contentType: 'application/json',
            success: function (result) {
                if (result.notice) {
                    display_flash_message(result.html, 1000);
                };
                if (action == 'delete') {
                    $(`.slide_container[name=${slide_id}]`).fadeOut(500, function () { $(this).remove() });
                };
                let count = result.count;
                if (mode == 'slide_cart') {
                    $('#slide_cart_count').html(count);
                    $('#slide_cart_count_container').css('display', count ? 'block' : 'none');
                } else if (mode == 'follow_ppt') {
                    $('#follow_ppt_count').html(count);
                    $('#follow_ppt_count_container').css('display', count ? 'block' : 'none');
                }
            },
            error: function (xhr, resp, text) {
                alert(`function ppt.add_to_slide_cart Error: ${text}`)
            }
        });
    }
}


// ajax to add all slide in slide cart to bookmark
function add_to_bookmark(event) {
    if (confirm('Sure to Bookmark all selected slides?')) {
        $.ajax({
            url: "{{url_for('ppt.add_to_bookmark')}}",
            type: "POST",
            success: function (result) {
                display_flash_message(result.html, 1000)
            }
        })
    }
};


// save edits to note and tag
function save_edit(envent, table, field, id) {
    let container = $(event.target).closest('.input_container');
    let value = $(event.target).parent().parent().find('input').val();
    //confirm(`Change ${field} to ${value}?`)
    if (true) {
        $.ajax({
            url: "{{url_for('ppt.edit')}}",
            type: "POST",
            data: JSON.stringify({ id: id, data: value, field: field, table: table }),
            contentType: "application/json",
            success: function (result) {
                display_flash_message(result.html, 1000);
                $(container).find('span.slide_tag').html(result.tag);
                $(container).find(`span.${table}_note`).html(result.note);
            },
            error: function (xhr, resp, text) { alert(`Save edit error: ${text}`) },
        });
    }
}



// update search menu's search in field based on current display page.
$(document).ready(function () {
    let table = "{{table}}";
    let option = [];
    $("#search_field option").each(function () { option.push($(this).val()) });
    if (option.includes(table)) {
        $("#search_field").val(table);
    };
});

// make reversecomp sequence:
function revcomp(seq) {
    const bpmap = { A: 'T', C: 'G', G: 'C', T: 'A', U: 'A' };
    let rev_comp = "";
    for (var i = seq.length - 1; i >= 0; i--) {
        revbp = bpmap[seq[i].toUpperCase()]
        if (revbp) {
            rev_comp += revbp;
        } else {
            rev_comp = "Not a valid sequence.";
            break
        };
    }
    return rev_comp
};

$(document).ready(function () {
    $('input#q[name="q"]').change(function (event) {
        let seq = event.target.value;
        let method = $("#search_method").val();
        seq = seq.split(" ").join("");
        if (method != 'text') {
            event.target.value = seq;
        }
        let rev_comp = revcomp(seq);
        $("#ngs_search_revcomp_seq").html(rev_comp);
    });
});

// update search allowed combinations.
function change_search_field(method) {
    let sequence = ['known_sequence', 'primer', 'sequence'];
    //let text = ['known_sequence', 'primer', 'selection', 'round', 'analysis', 'ngs_sample_group',];
    if (method != 'text' && method != 'name') {
        $('#ngs_search_revcomp_container').css('display', 'block');
        $("#search_field option").each(function () {
            if (sequence.includes($(this).val())) { $(this).removeAttr('disabled') }
            else { $(this).attr('disabled', "") };
        });
        if (!sequence.includes($("#search_field").val())) {
            $("#search_field").val("known_sequence")
        };
    }
    else if (method == 'name') {
        $('#ngs_search_revcomp_container').css('display', 'none');
        $("#search_field option").each(function () {
            $(this).removeAttr('disabled');
        });
    }
    else {
        $('#ngs_search_revcomp_container').css('display', 'none');
        $("#search_field option").each(function () {
            $(this).removeAttr('disabled');
            //if (text.includes($(this).val())) { $(this).removeAttr('disabled') }
            //else { $(this).attr('disabled', "") };
        });
        /* if (!text.includes($("#search_field").val())) {
                     $("#search_field").val("selection")
                 }*/
    }
}

// change
$(document).ready(function () {
    let method = $("#search_method").val();
    change_search_field(method);
    $("#search_method").change(function (event) {
        let method = event.target.value;
        change_search_field(method);
    })
});




$(document).ready(function () {
    $("#search_project").change(function (event) {
        let projectid = event.target.value;
        change_search_ppt(projectid);
    })
});

function change_search_ppt(projectid) {
    $.ajax({
        url: "{{url_for('ppt.get_ppt_by_project')}}",
        type: 'POST',
        data: JSON.stringify({ project: projectid }),
        contentType: "application/json",
        success: function (result) {
            let options = '<option selected value="all">All</option>';
            for (let opt of result.options) {
                options += `<option value="${opt[0]}">${opt[1]}</option>`
            };
            $('#search_ppt').html(options);
        }
    })
};
$(document).ready(function () {
    //change_search_ppt(projectid);
    $("#search_field").change(function (event) {
        let field = event.target.value;
        if (field == 'tag') {
            $('#query_input').attr('list', "tags_list")
        } else {
            $('#query_input').removeAttr('list');
        }
    })
});


// monitor key board  F for search.
$(document).ready(function () {
    $(document).keypress(function (e) {
        var c = String.fromCharCode(e.which);
        if (e.target.tagName == 'BODY' && c === 'f') {
            $('#search_dialog').modal('show');
        }
    });
});

// follow a powerpoint or unfollow a powerpoint. definded here for index page use as well
function add_ppt_to_follow(event) {
    let ppt_id = $(event.target).attr('name');
    let action = $(event.target).text();
    $.ajax({
        url: "{{url_for('ppt.add_ppt_to_follow')}}",
        type: "POST",
        data: JSON.stringify({ ppt_id: ppt_id, action: action }),
        contentType: "application/json",
        success: function (result) {
            display_flash_message(result.html, 1000);
            if (!result.status) {
                $(event.target).text('Follow');
                $(event.target).removeClass('label-warning').addClass('label-info')
            } else {
                $(event.target).text('Unfollow');
                $(event.target).removeClass('label-info').addClass('label-warning')
            }
        },
        error: function (xhr, resp, text) { alert(`Save Flag error: ${text}`) },
    })
}


