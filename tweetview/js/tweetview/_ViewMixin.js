// Provide the class
dojo.provide("tweetview._ViewMixin");

// Declare the class
dojo.declare("tweetview._ViewMixin", null, {
	// Returns this pane's list
	getListNode: function() {
		//return dojo.query(".tweetviewList",this.domNode)[0];
		//return this.domNode.getElementsByClassName()[0];
		return this.getElements("tweetviewList", this.domNode)[0];
	},
	// Updates the list widget's state
	showListNode: function(show) {
		dojo[(show ? "remove" : "add") + "Class"](this.listNode, "tweetviewHidden");
	},
	// Pushes data into a template - primitive
	substitute: function(template,obj) {
		return template.replace(/\$\{([^\s\:\}]+)(?:\:([^\s\:\}]+))?\}/g, function(match,key){
			return obj[key];
		});
	},
	// Get elements by CSS class name
	getElements: function(cssClass,rootNode) {
		return (rootNode || dojo.body()).getElementsByClassName(cssClass);
	}
});