this.provide = function() {
    var namespace = this;
    var provide = this.provide;
    $.each(arguments, function(i, name) {
        if (!namespace[name]) {
            namespace[name] = {};
        }
        namespace = namespace[name];
        namespace.provide = provide;
    });
};

provide('pushmaster');

//
// location
//

pushmaster.provide('location');

pushmaster.location.queryToObject = function(query) {
    var object = {};
    if (query) {
        if (query.charAt(0) == '?') {
            query = query.substring(1);
        }
        $.each(query.split('&'), function(i, pair) {
            var parts = $.map(pair.split('='), function(part) {
                return decodeURIComponent(part.replace(/\+/g, '%20'));
            });
            object[parts[0]] = parts[1];
        });
    }
    return object;
};

pushmaster.location.reload = function() {
    if (location.hash) {
        location.reload();
    } else {
        location.replace(location.href);
    }
};

pushmaster.location.query = pushmaster.location.queryToObject(location.search);

//
// XHRs
//

pushmaster.provide('xhr');

pushmaster.xhr.get = function(options) {
    options = $.extend({'dataType': 'json'}, options, {'type': 'get'});
    return $.ajax(options);
};

//
// dialogs
//

pushmaster.provide('dialog');

pushmaster.dialog.Dialog = function() {};
pushmaster.dialog.Dialog.prototype = {
    initialized: false,

    ensureDialog: function() {
        if (!this.initialized) {
            this.form.dialog(this.dialogOptions);
            this.initialized = true;
        }
    },

    isOpen: function() {
        return this.initialized && this.form.dialog('isOpen');
    },

    open: function() {
        this.ensureDialog();
        if (!this.form.dialog('isOpen')) {
            this.form.dialog('open');
        }
        return this;
    },

    close: function() {
        if (this.initialized && this.form.dialog('isOpen')) {
            this.form.dialog('close');
        }
        return this;
    },

    toggle: function() {
        if (this.initialized && this.form.dialog('isOpen')) {
            this.close();
        } else {
            this.open();
        }
        return this;
    }
};

pushmaster.dialog.MakeRequest = function() {
    this.form = $('#new-request-form');

    if (location.search) {
        var query = pushmaster.location.queryToObject(location.search);

        var shouldOpen = false;
        ['subject', 'message', 'branch'].forEach(function(param) {
            if (query[param]) {
                this.form.find('[name=' + param + ']').val(query[param]);
                shouldOpen = true;
            }
        }, this);

        if (shouldOpen) {
            this.open();
        }
    }
    this.constructor.prototype.constructor.call(this);
};
pushmaster.dialog.MakeRequest.prototype = $.extend(new pushmaster.dialog.Dialog(), {
    dialogOptions: {
        'title': 'Make Request',
        'width': 700,
        'height': 500,
        'position': ['center', 100]
    }
});

pushmaster.dialog.StartPush = function() {
    this.form = $('#new-push-form');
    this.constructor.prototype.constructor.call(this);
};
pushmaster.dialog.StartPush.prototype = $.extend(new pushmaster.dialog.Dialog(), {
    dialogOptions: {
        'title': 'Start Push',
        'width': 500,
        'height': 100,
        'position': ['center', 100]
    }
});

pushmaster.dialog.SendToStage = function() {
    this.form = $('#sendtostage-form');
    this.constructor.prototype.constructor.call(this);
};
pushmaster.dialog.SendToStage.prototype = $.extend(new pushmaster.dialog.Dialog(), {
    dialogOptions: {
        'title': 'Send to Stage',
        'width': 500,
        'height': 100,
        'position': ['center', 100]
    },

    setAction: function(action) {
        this.form.attr('action', action);
        return this;
    }
});

pushmaster.dialog.RejectRequest = function() {
    this.form = $('#reject-request-form');
    this.constructor.prototype.constructor.call(this);
};
pushmaster.dialog.RejectRequest.prototype = $.extend(new pushmaster.dialog.Dialog(), {
    dialogOptions: {
        'title': 'Reject Request',
        'width': 500,
        'height': 300,
        'position': ['center', 100]
    },

    setRequest: function(request) {
        this.form.attr('action', request.uri);
        this.form.find('[name=return_url]').val(location.href);
        this.form.find('.subject').text(request.subject);
        return this;
    }
});

//
// events
//

pushmaster.provide('event');

pushmaster.event.preventDefaultEmptyHref = function(e) {
    var href = $(e.target).closest('a').attr('href');
    if (href.charAt(href.length - 1) === '#') {
        e.preventDefault();
    }
};

pushmaster.event.toggleFormContent = function(e) {
    $(e.target)
        .closest('form')
        .find('div.content')
        .toggle();
};

pushmaster.event.toggleDetails = function(e) {
    $('body').toggleClass('details');
};

//
// page
//

pushmaster.provide('page');

//
// init
//

(function() {
    // # hrefs
    $('a').live('click', pushmaster.event.preventDefaultEmptyHref);

    // form toggler
    $('a.toggle').live('click', pushmaster.event.toggleFormContent);

    // request details toggle
    $('a#details').live('click', pushmaster.event.toggleDetails);

    // request dialog
    $(function() {
        pushmaster.page.makeRequest = new pushmaster.dialog.MakeRequest();
        $('#new-request').click(function(e) {
            pushmaster.page.makeRequest.toggle();
        });
    });

    // new push dialog
    $(function() {
        pushmaster.page.startPush = new pushmaster.dialog.StartPush();
        $('#new-push').click(function(e) {
            pushmaster.page.startPush.toggle();
        });
    });

    // send to stage dialog
    $(function() {
        pushmaster.page.sendToStage = new pushmaster.dialog.SendToStage();
        var send_button = $('#send-to-stage');
        if(send_button) {
            pushmaster.page.sendToStage.setAction(send_button.attr('value'));
            send_button.click(function(e) {
                pushmaster.page.sendToStage.toggle();
            });
        }
    });

    // reject request dialog
    $(function() {
        pushmaster.page.rejectRequest = new pushmaster.dialog.RejectRequest();
        $('a.reject-request').live('click', function(e) {
            e.preventDefault();
            var link = $(e.target).closest('a');
            pushmaster.page.rejectRequest
                .setRequest({'uri': link.attr('href'), 'subject': link.attr('title')})
                .toggle();
        });
    });

    // datepickers
    $(function() {
        $('input.date').datepicker({ 
            'showAnim': 'fadeIn',
            'dateFormat': 'yy-mm-dd',
            'minDate': new Date()
        });
    });
})();

