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

var ansispan = function (str) {
  str = str.replace(/\r\n/mg, "\n");
  while( !(str.indexOf("\r") === -1) ) {
    str = str.replace(/^.*\r([^\r]*)$/mg, "$1")
  }
  Object.keys(ansispan.foregroundColors).forEach(function (ansi) {
    var span = '<span style="color: ' + ansispan.foregroundColors[ansi] + '">';

    //
    // `\033[Xm` == `\033[0;Xm` sets foreground color to `X`.
    //

    str = str.replace(
      new RegExp('\033\\[' + ansi + 'm', 'g'),
      span
    ).replace(
      new RegExp('\033\\[0;' + ansi + 'm', 'g'),
      span
    );
  });
  //
  // `\033[1m` enables bold font, `\033[22m` disables it
  //
  str = str.replace(/\033\[1m/g, '<span style="font-weight: bold;">').replace(/\033\[22m/g, '</span>');

  //
  // `\033[3m` enables italics font, `\033[23m` disables it
  //
  str = str.replace(/\033\[3m/g, '<span style="font-style: italic;>').replace(/\033\[23m/g, '</span>');

  // this is ugly as hell and not xhtml, but it works
  // the browser will close my tags until parent pre close
  // contact me with better ideas...
  exitstr = '<span style="color: #333; font-weight: normal; font-style: normal;">'

  str = str.replace(/\033\[m/g, exitstr);
  str = str.replace(/\033\[0m/g, exitstr);

  // universal reset
  str = str.replace(/\033\(B/g, exitstr);

  return str.replace(/\033\[39m/g, exitstr);
};

ansispan.foregroundColors = {
  '30': 'black',
  '31': '#bd362f', // red
  '32': '#51a351', // green
  '33': '#f89406', // yellow
  '34': '#0044cc', // blue
  '35': 'purple',
  '36': '#2f96b4', // cyan
  '37': 'white'
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = ansispan;
}

