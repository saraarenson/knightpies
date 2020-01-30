FALSE R1 ; 0 so FPUTC uses standard out
FALSE R2 ; 0 to be at top of address space
LOADUI R2 $deadbeef
LOAD8 R0 R2 -4 ; load the 8 bits at R2+$testdata into R0
FPUTC		       ; write contents of R0 to standard out
;ADDUI R2 R2 1	       ; move pointer ahead one character
;LOADU8 R0 R2 -1
LOAD8 R0 R2 -3
FPUTC
HALT
:testdata
"I
think that I should never see"
"A poem lovely as a tree"
:deadbeef
'dead'
'beef'
