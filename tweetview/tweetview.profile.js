dependencies = {
	stripConsole: "normal",
	layers: [
		{
			name: "../tweetview/tweetview.js",
			dependencies: [
				"tweetview.TweetView",
				"tweetview.SettingsView",
				"dojox.mobile.TabBar",
				"dojox.mobile"
			]
		}
	],

	prefixes: [
		[ "dijit", "../dijit" ],
		[ "dojox", "../dojox" ],
		[ "tweetview", "../tweetview" ]
	]
}
