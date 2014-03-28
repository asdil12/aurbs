/*
 * Copyright (C) 2011 by Maciej Małecki
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 *
 * https://github.com/mmalecki/ansispan/
 *
 */


/*
 * see http://en.wikipedia.org/wiki/ANSI_escape_code#Colors
 *
 * Sequence start: »\033[«
 * Sequence end:   »m«
 * Sequence content: SGR parameters, seperated with »;«
 */

var ansispan = function (str) {
	str = str.replace(/\r\n/mg, "\n");
	while( !(str.indexOf("\r") === -1) ) {
		str = str.replace(/^.*\r([^\r]*)$/mg, "$1")
	}

	str = str.replace(/\033\[([^m]*)m/g, function(sequence) {
		var sgr_params = RegExp.$1.split(';');
		var style = [];
		if (sgr_params.length == 0 || sgr_params.indexOf('0') > -1) {
			style.push( "sgr0" );
		}
		else {
			sgr_params.forEach(function(sgr) {
				style.push( 'sgr' + sgr );
			});
		}
		return '<span class="' + style.join(' ') + '">';
	});

	return str;
};


if (typeof module !== 'undefined' && module.exports) {
  module.exports = ansispan;
}

