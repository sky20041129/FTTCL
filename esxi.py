import os

#esxcli software vib list | grep Fujitsu
#esxcli software vib install -v /tmp/xxx.vib --no-sig-check△--maintenance-mode
#esxcli software vib list | grep Fujitsu


def raid_esxi_tool_update():
 
    print("     Current tool version          ")
    os.system("esxcli software vib list | grep Fujitsu")
    print("                                   ")


    print("List the file:")
    lin = os.popen("ls |grep -i .vib").readlines()
    print (lin)

    x = input("Please input the line of file:")
    linefile = lin[int(x)].rstrip()
    print("                             ")

    os.system("esxcli software vib install -v /tmp/%s --no-sig-check --maintenance-mode" %(linefile))


raid_esxi_tool_update()
print("Please restart the system after installation.")
