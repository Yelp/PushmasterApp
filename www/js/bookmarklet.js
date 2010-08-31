(function() {
    var elementToText = function(i, a) {
        return $(a).text(); 
    };

    var ticketNumberToURL = function(bug) { 
        return 'https://trac.yelpcorp.com/ticket/' + bug.match(/\d+/)[0];
    };

    var summary = $('#summary').text();
    var codeReview = location.href.split('#')[0];
    var reviewers = $('div.shipit').closest('div[id^=review]').find('div.reviewer >a, a[name=last-review] >a').map(elementToText).get();
    var tickets = $('#bugs_closed').text().split(',').filter(Boolean).map(ticketNumberToURL);
    var branch = $('#branch').text();
    
    var message = [];
    if (reviewers.length > 0) {
        message.push(codeReview, ' by ', reviewers.join(', '));
    }
    if (tickets.length > 0) {
        if (message.length > 0) {
            message.push('\n\n');
        }
        message.push(tickets.length == 1 ? 'Ticket: ' : 'Tickets: ', tickets.join(', '));
    }
    message = message.join('');

    location.href = 'http://yelp-pushmaster.appspot.com/requests?' + $.param({'subject': summary, 'message': message, 'branch': branch});
})();