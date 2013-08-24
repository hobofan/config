var humanMsg = {
	setup: function(appendTo, logName, msgOpacity) {
		humanMsg.msgID = 'human-message';

		// appendTo is the element the msg is appended to
		if (appendTo == undefined) appendTo = 'body';

		// Opacity of the message
		humanMsg.msgOpacity = .8;

		if (msgOpacity != undefined) humanMsg.msgOpacity = parseFloat(msgOpacity);

		// Inject the message structure

		jQuery(appendTo).append('<div id="'+humanMsg.msgID+'" class="humanMsg"><div class="round"></div><p></p><div class="round"></div></div>')

		window.alert = humanMsg.displayMsg;
		window.infinite = Infinity;
	},

	displayMsg: function(msg, options) {
		if (msg == '') return;

		if (options != undefined) {
			delay = 'delay' in options ? parseInt(options.delay) * 1000 : 1000
			life = 'life' in options ? parseInt(options.life) * 1000 : infinite
		} else {
			delay = 1000
			life = infinite
		}

		// Inject message
		jQuery('#'+humanMsg.msgID+' p').html(msg);

		// Show message
		clearTimeout(humanMsg.t2);

		jQuery('#'+humanMsg.msgID+'').show().animate({ opacity: humanMsg.msgOpacity})

		// Watch for mouse & keyboard in 2s
		humanMsg.t1 = setTimeout("humanMsg.bindEvents()", delay)

		// Remove message after 10s
		humanMsg.t2 = setTimeout("humanMsg.removeMsg()", life)
	},


	bindEvents: function() {
	// Remove message if mouse is moved or key is pressed
		jQuery(window)
			.mousemove(humanMsg.removeMsg)
			.click(humanMsg.removeMsg)
			.keypress(humanMsg.removeMsg)
	},



	removeMsg: function() {
		// Unbind mouse & keyboard
		jQuery(window)
			.unbind('mousemove', humanMsg.removeMsg)
			.unbind('click', humanMsg.removeMsg)
			.unbind('keypress', humanMsg.removeMsg)

		// If message is fully transparent, fade it out
		if (jQuery('#'+humanMsg.msgID).css('opacity') == humanMsg.msgOpacity) {
			jQuery('#'+humanMsg.msgID).animate({ opacity: 0 }, 500, function() { jQuery(this).hide() })
		}
	}
};

jQuery(document).ready(function(){
	humanMsg.setup();
})
