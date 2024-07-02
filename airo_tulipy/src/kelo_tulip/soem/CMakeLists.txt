if(WIN32)
	set(SOEM_OS_SOURCE_FILES
            osal/win32/osal.c
            oshw/win32/nicdrv.c
            oshw/win32/oshw.c
	)		
else(WIN32)
	set(SOEM_OS_SOURCE_FILES
            osal/linux/osal.c
            oshw/linux/nicdrv.c
            oshw/linux/oshw.c
	)		
endif(WIN32)

ADD_LIBRARY(soem STATIC
	ethercatbase.c
	ethercatcoe.c
	ethercatconfig.c
	ethercatdc.c
	ethercatfoe.c
	ethercatmain.c
	ethercatprint.c
	ethercatsoe.c
	${SOEM_OS_SOURCE_FILES}
)

INSTALL(TARGETS soem
	ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
	PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDE_DIR}
)
