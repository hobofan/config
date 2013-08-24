function setup_switch() {
	var select = this;
	var placeholder = document.createElement('SPAN');
	$(placeholder)
		.addClass('placeholder')
		.click(function () {
			select.selectedIndex = Math.abs(1 - select.selectedIndex);
			$(select).change();
			$(placeholder).text(get_value.call(select));
		})
		.text(get_value.call(this));
	$(this)
		.before(placeholder)
		.hide();
}

function get_value() {
	switch (this.localName) {
		case 'INPUT':
			return this.value ? this.value : this.defaultValue;
			break;
		case 'SELECT':
			var result = $(this).find('option[value=' + this.value + ']')
			if (result) { return result.slice(0, 1).text() }
			else { return this.value }
			break;
	}
}

function setup_input() {
	if (this.localName == 'SELECT' && this.options.length == 2) { return setup_switch.call(this); }
	var placeholder = document.createElement('SPAN');
	var input = this;

	function show() {
		$(placeholder).hide();
		$(input).show().focus()
	}
	function done() {
		$(this).hide();
		$(placeholder).show().text(get_value.call(this));
	}

	$(placeholder)
		.addClass('placeholder')
		.click(show)
		.text(get_value.call(this));
	$(this)
		.blur(done)
		.before(placeholder)
		.hide();
	if (this.localName == 'SELECT') { this.size = this.options.length }
}

function setup_items() {
	$(this).filter(function() {
			return (this.localName == 'INPUT' && this.type == 'text') || this.localName == 'SELECT'
		}).each(setup_input);
}

$(document).ready(function() { $('.sentence').find('textarea, input, select').each(setup_items); })
