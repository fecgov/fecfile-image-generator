#!/bin/sh
/usr/bin/xvfb-run -a --server-args="-screen 0, 1024x768x24" /usr/bin/wkhtmltopdf -q --no-pdf-compression --encoding 'UTF-8' $*
