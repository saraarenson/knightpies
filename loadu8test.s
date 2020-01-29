FALSE R1
LOADU8 R0 R1 @testdata
FPUTC
ADDUI R1 R1 1
LOADU8 R0 R1 @testdata
FPUTC
HALT
:testdata
"I
think that I should never see"
"A poem lovely as a tree"
'dead'
'beef'