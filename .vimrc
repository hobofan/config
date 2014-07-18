execute pathogen#infect()
syntax on
filetype plugin indent on
set background=dark
set number
colorscheme solarized
set shiftwidth=2
set expandtab
set tabstop=2
set laststatus=2
set encoding=utf-8
set t_Co=256
let mapleader=","
"au BufNewFile,BufReadPost *.coffee setl shiftwidth=2 expandtab
au BufNewFile,BufReadPost *.rb setl shiftwidth=2 expandtab
au BufNewFile,BufReadPost *.cap setl shiftwidth=2 expandtab
au BufNewFile,BufReadPost *.rake setl shiftwidth=2 expandtab
"au BufNewFile,BufReadPost *.erb setl shiftwidth=2 expandtab
let g:Powerline_symbols = 'fancy'
let g:atp_Compiler='bash'
let g:rubycomplete_buffer_loading = 1
let g:rubycomplete_classes_in_global = 1 
let g:rubycomplete_rails = 1

cmap w!! w !sudo tee > /dev/null % 

"Display all non-whitespace characters as something
set listchars=eol:$,tab:>-,trail:~,extends:>,precedes:<
set list

let mapleader = ","
