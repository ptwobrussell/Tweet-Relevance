// Provide the UI class
dojo.provide("tweetview.TweetView");

// Dependencies here
dojo.require("tweetview._ViewMixin");
dojo.require("dojox.mobile.ScrollableView");
dojo.require("dojo.DeferredList");
dojo.require("dojo.io.script");

// Require localization for time
dojo.require("dojo.i18n");
dojo.requireLocalization("dojo.cldr", "gregorian", "", "");

// Declare the class;  inherits from ScrollableView
dojo.declare("tweetview.TweetView", [dojox.mobile.ScrollableView, tweetview._ViewMixin], {
	
	// Create a template string for tweets:
	tweetTemplateString: '<img src="${avatar}" alt="${name}" class="tweetviewAvatar" />' + 
	'<div class="tweetviewTime" data-dojo-time="${created_at}">${time}</div>' +
	'<div class="tweetviewContent"> ' +
		'<div class="tweetviewUser">${user}</div>' + 
		'<div class="tweetviewText">${text}</div>' + 
	'</div><div class="tweetviewClear"></div>',
	
	// Icon for loading...
	iconLoading: dojo.moduleUrl("tweetview", "resources/images/loading.gif"),
	// iconLoading: dojo.moduleUrl("tweetview", "resources/images/androidLoading.gif"),
	
	// URL to pull tweets from
	serviceUrl: "",

	// When the widgets have started....
	startup: function() {

		// Retain functionality of startup in dojox.mobile.ScrollableView
		this.inherited(arguments);
		
		// Get the refresh button and image
		this.refreshButton = dijit.byId(this.getElements("tweetviewRefresh", this.domNode)[0].id);
		this.iconImage = this.refreshButton.iconNode.src;
		
		// Add a click handler to the button that calls refresh
		dojo.connect(this.refreshButton, "onClick", this, "refresh");
		
		// Add CSS class for styling
		dojo.addClass(this.domNode, "tweetviewPane");
		
		// Get the list widget
		this.listNode = this.getListNode();
		
		// Hide the list because it's not populated with list items yet
		this.showListNode(false);
		
		// Get localization for tweet times
		// Get the i18n
		this.l10n = dojo.i18n.getLocalization("dojo.cldr", "gregorian");
		
		// Every 60 seconds, update the times
		setInterval(dojo.hitch(this, function() {
			//dojo.query(".tweetviewTime",this.domNode).forEach(function(timeNode) {
			dojo.forEach(this.getElements("tweetviewTime",this.domNode), function(timeNode) {
				timeNode.innerHTML = this.formatTime(dojo.attr(timeNode, "data-dojo-time"));
			},this);
		}),60000);

        // Manually trigger initial loading of content by simulating a "refresh"
        this.refresh();
	},
	
	// Contacts twitter to receive tweets
	refresh: function() {
		// Updates the refresh icon
		this.refreshButton.iconNode.src = this.iconLoading;

		// Button has been "pressed"
		this.refreshButton.select();
	
        // Use sid to fetch data computed during previous call to /app
        var uri = document.location.href;
        var query = uri.substring(uri.indexOf("?") + 1, uri.length);
        var queryObject = dojo.queryToObject(query);
        var dataUrl = "/data";

        dojo.xhrGet({
            url : dataUrl,
            content : {sid : queryObject.sid},
            handleAs : "json",
            load : dojo.hitch(this, function(response) {
                // Set the refresh icon back
                this.refreshButton.iconNode.src = this.iconImage;
                this.refreshButton.select(true);

                // Sort by date tweeted
                response.sort(function(a, b) {
                    var atime = new Date(a.created_at),
                        btime = new Date(b.created_at);
                    console.log(atime - btime);
                    return atime - btime;
                });

                this.updateContent(response);

                return response
            }),
            error : function(error) {
                console.error(error);
                return error;
            }
        });
	},
	
	// Fires when tweets are received from the controller
	updateContent: function(rawTweetData) {
		// For every tweet received....
		dojo.forEach(rawTweetData, function(tweet) {
			// Get the user's screen name
			var screenName = tweet.user.screen_name;
			
			// Create a new list item, inject into list
			var item = new dojox.mobile.ListItem({
				"class": "tweetviewListItem user-" + screenName
			}).placeAt(this.listNode,"first");
			
			// Update the list item's content using our template for tweets
			item.containerNode.innerHTML = this.substitute(this.tweetTemplateString, {
				text: this.formatTweet(tweet.text),
				user: tweet.from_user || screenName,
				name: tweet.from_user || tweet.user.name,
				avatar: tweet.profile_image_url || tweet.user.profile_image_url,
				time: this.formatTime(tweet.created_at),
				created_at: tweet.created_at,
				id: tweet.id
			});
		}, this);
        
		// Show the list now that we have content for it
		this.showListNode(true);
	},
	
	// Adds the proper tweet linkification to a string
	formatTweet: function(tweetText) {
		return tweetText.
		replace(/(https?:\/\/\S+)/gi,'<a href="$1">$1</a>').
		replace(/(^|\s)@(\w+)/g,'$1<a href="http://twitter.com/$2">@$2</a>').
		replace(/(^|\s)#(\w+)/g,'$1<a href="http://search.twitter.com/search?q=%23$2">#$2</a>');
	},
	
	// Formats the time as received by Twitter
	formatTime: function(date) {
		// Get now
		var now = new Date();
		
		// Push string date into an Date object
		var tweetDate = new Date(date);
		
		// Time measurement: seconds
		var secondsDifferent = Math.floor((now - tweetDate) / 1000);
		if(secondsDifferent < 60) {
			return secondsDifferent + " " + (this.l10n['field-second']) + (secondsDifferent > 1 ? "s" : "");
		}
		
		// Time measurement: Minutes
		var minutesDifferent = Math.floor(secondsDifferent / 60);
		if(minutesDifferent < 60) {
			return minutesDifferent + " " + this.l10n['field-minute'] + (minutesDifferent > 1 ? "s" : "");
		}
		
		// Time measurement: Hours
		var hoursDifferent = Math.floor(minutesDifferent / 60);
		if(hoursDifferent < 24) {
			return hoursDifferent + " " + this.l10n['field-hour'] + (hoursDifferent > 1 ? "s" : "");
		}
		
		// Time measurement: Days
		var daysDifferent = Math.floor(hoursDifferent / 24);
		return daysDifferent + " " + this.l10n['field-day'] + (daysDifferent > 1 ? "s" : "");
	}
	
});
