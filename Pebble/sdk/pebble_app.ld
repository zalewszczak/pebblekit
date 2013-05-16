ENTRY(pbl_main)

MEMORY
{
  APP (rwx) : ORIGIN = 0, LENGTH = 24K
}

SECTIONS
{
  .header : { KEEP(*(.pbl_header)) } > APP
  .text : { *(.text) } > APP
  .data : { KEEP(*(.data)) } > APP
  .bss : { *(.bss) } > APP

    DISCARD :
    {
     libc.a ( * )
     libm.a ( * )
     libgcc.a ( * )
     *(.eh_frame)
    }
}
