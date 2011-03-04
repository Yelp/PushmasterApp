pushmaster.provide('push');

pushmaster.push.pageReloadDelay = 30 * 1000; // ms

pushmaster.push.retrievePushData = function() {
    if (push.state !== 'live' && !pushmaster.location.query.noreload) {
        pushmaster.push.retrieveTimeout = setTimeout(function() {
            pushmaster.push.retrieveTimeout = null;
            pushmaster.xhr.get({
                'url': location.pathname + '/json',
                'success': pushmaster.push.loadPushData,
                'error': pushmaster.push.retrievePushData});
        }, pushmaster.push.pageReloadDelay);
    }
};

pushmaster.push.loadPushData = function(pushData) {
    push.state = pushData.push.state;
    $('.push').html(pushData.html);
    pushmaster.push.retrievePushData();
};

//
// init
//

$(pushmaster.push.retrievePushData);
