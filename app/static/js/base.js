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
            $('ul.nav a[href*="' + url + '"]').filter(function () { return $(this).attr('name') != 'badge_icon' }).parent().addClass('active');
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