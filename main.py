from tkinter import ttk
from tkinter import *
from PIL import Image, ImageTk
import datetime
from Ulity import *
from FAT32 import *
from NTFS import *


class App(Tk):

    def __init__(self):
        Tk.__init__(self)
        # Config main window
        app_width = 1000
        app_height = 600
        x, y = findCenterPoint(self, app_width, app_height)

        self.geometry(f'{app_width}x{app_height}+{int(x)}+{int(y)}')
        self.configure(bg="white")
        # self.resizable(False, False)
        self.title('FAT32/NTFS')

        # Main frame to change between page
        self.container = Frame(self)
        self.container.pack(side="top", fill="both", expand=True)

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.show_frame(VolumeListDisplay)

        # STYLE configuration
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview.Heading", font=('Calibri', 13, 'bold'),
                        background='#D6EAF8', foreground='#34495E', relief=RIDGE)
        style.configure("Treeview", font=('Calibri', 11),
                        rowheight=24, foreground='#34495E')
        style.map('Treeview.Heading', background=[('active', '#81AFDE')])

    def show_frame(self, cont):
        frame = cont(self.container, self)
        frame.grid(row=0, column=0, sticky="nsew")


class VolumeListDisplay(Frame):  # Display list of Volume

    def __init__(self, root, controller):
        Frame.__init__(self, root)
        self.config(bg='#F7F9F9')
        self.controller = controller

        Label(self, text='External Drives', font=('Calibri', 20,
              'bold'), bg='#F7F9F9', fg='#3498DB').grid(row=0,
                                                        column=0,
                                                        padx=10,
                                                        pady=5,
                                                        sticky=NW)

        self.drive_icon = ImageTk.PhotoImage(Image.open(
            'Images\Drive.png').resize((50, 50), Image.Resampling.LANCZOS))

        self.volumes = get_external_drive()

        self.btn_lst = []
        # self.clicked = 0
        self.cur_btn = ()
        if self.volumes:
            self.but()
        else:
            Label(self, text='Oops, you don\'t have any external volumes!!!', font=(
                'Calibri', 14, 'italic'), bg='#F7F9F9', fg='#3498DB').place(x=500, y=150, anchor=CENTER)

    def hover(self, e):
        but = e.widget
        but['bg'] = '#E5E7E9'

    def hover_leave(self, e):
        # if self.clicked == 1:
        #     return
        but = e.widget
        if but == self.cur_btn:
            return
        but['bg'] = '#F7F9F9'

    # def on_click(self):
    #     if self.cur_btn:
    #         self.cur_btn['bg'] = '#F7F9F9'
    #     x, y = self.controller.winfo_pointerxy()
    #     self.cur_btn = self.controller.winfo_containing(x, y)
    #     # self.clicked = 1
    #     self.cur_btn['bg'] = '#E5E7E9'

    def on_double_click(self, e):
        but = e.widget
        but.config(cursor='watch')
        self.update_idletasks()

        if isinstance(but, Button):
            for i in range(len(self.volumes)):
                if self.btn_lst[i] == but:
                    global vol_name
                    vol_name = self.volumes[i]
                    global file_tree
                    if FAT32Vol.CheckFat32(self.volumes[i]):
                        file_tree = FAT32Vol(vol_name).ListElement()
                    elif NTFSVol.check_ntfs(self.volumes[i]):
                        file_tree = NTFSVol(vol_name).ListElement()

                    break

        for widget in self.winfo_children():
            widget.destroy()
        self.controller.show_frame(FileExplorer)

    def but(self):
        for i in range(len(self.volumes)):
            self.btn_lst.append(Button(self, padx=20, pady=7, border=0, bg='#F7F9F9', fg='#3498DB',  activebackground='#F7F9F9', text='('+self.volumes[i]+')', image=self.drive_icon,  width=200,
                                       height=50, compound=LEFT, relief=RIDGE, font=('Calibri', 15)))
            self.btn_lst[-1].grid(row=i // 3+1, column=i %
                                  3, padx=20, pady=5, sticky=W)
            menu = Menu(self.btn_lst[-1], tearoff=0)

            def on_btn_2(e):
                # if self.clicked == 0:
                #     self.clicked = 1
                self.cur_btn = e.widget
                self.cur_btn['bg'] = '#E5E7E9'
                try:
                    menu.tk_popup(e.x_root, e.y_root)
                finally:
                    self.cur_btn['bg'] = '#F7F9F9'
                    # self.clicked = 0
                    self.cur_btn = None
                    menu.grab_release()

            def on_properties():
                x, y = self.controller.winfo_pointerxy()
                but = self.controller.winfo_containing(x, y)
                but.config(cursor='watch')
                self.update_idletasks()

                for i in range(len(self.volumes)):
                    if self.btn_lst[i] == but:
                        vol_name = self.volumes[i]
                        info = ()

                        newWindow = Toplevel(self.controller)
                        newWindow.title('('+vol_name+') Properties')
                        window_width = 400
                        window_height = 300
                        x, y = findCenterPoint(
                            self.controller, window_width, window_height)
                        newWindow.geometry(
                            f'{window_width}x{window_height}+{int(x)}+{int(y)}')

                        text_area = Text(newWindow, font=(
                            'Calibri', 11), bg='#F2F2F2', border=0, foreground='#34495E')
                        text_area.config(spacing3=10)

                        text = []
                        if FAT32Vol.CheckFat32(self.volumes[i]):
                            info = FAT32Vol(vol_name).getBootSector()
                            text.append('Bytes Per Sector:\t\t\t\t' +
                                        str(info['Bytes Per Sector']))
                            text.append(
                                '\nSectors Per Cluster:\t\t\t\t' + str(info['Sectors Per Cluster']))
                            text.append('\nReserved Sectors:\t\t\t\t' +
                                        str(info['Reserved Sectors']))
                            text.append('\nNumber of FAT:\t\t\t\t' +
                                        str(info['No of FAT']))
                            text.append(
                                '\nNumber of Sectors In Volume:\t\t\t\t' + str(info['No Sectors In Volume']))
                            text.append('\nSectors Per FAT:\t\t\t\t' +
                                        str(info['Sectors Per FAT']))
                            text.append(
                                '\nStarting Cluster of RDET:\t\t\t\t'+str(info['Starting Cluster of RDET']))
                            text.append('\nFAT Name:\t\t\t\t'+info['FAT Name'])
                            text.append(
                                '\nStarting Sector of Data:\t\t\t\t'+str(info['Starting Sector of Data']))
                        elif NTFSVol.check_ntfs(self.volumes[i]):
                            info = NTFSVol(vol_name).getBootSector()
                            text.append('OEM ID:\t\t\t\t' + info['OEM_ID'])
                            text.append('\nBytes Per Sector:\t\t\t\t' +
                                        str(info['Bytes Per Sector']))
                            text.append('\nSectors Per Cluster:\t\t\t\t' +
                                        str(info['Sectors Per Cluster']))
                            text.append('\nReserved Sectors:\t\t\t\t' +
                                        str(info['Reserved Sectors']))
                            text.append(
                                '\nNumber of Sectors In Volume:\t\t\t\t'+str(info['No. Sectors In Volume']))
                            text.append(
                                '\nFirst Cluster of $MFT:\t\t\t\t'+str(info['First Cluster of $MFT']))
                            text.append(
                                '\nFirst Cluster of $MFTMirr:\t\t\t\t'+str(info['First Cluster of $MFTMirr']))
                            text.append('\nClusters Per File Record Segment:\t\t\t\t' +
                                        str(info['Clusters Per File Record Segment']))
                            text.append('\nMFT record size:\t\t\t\t' +
                                        str(info['MFT record size']))
                            text.append('\nSerial Number:\t\t\t\t' +
                                        info['Serial Number'])
                            text.append('\nSignature:\t\t\t\t' +
                                        str(info['Signature']))

                        text_area.insert(1.0, '')
                        for t in text:
                            text_area.insert(END, t)
                        text_area.pack(expand=1, fill=BOTH, padx=10, pady=10)
                        text_area.config(state=DISABLED)

                but.config(cursor='arrow')

            menu.add_command(label='Properties', command=on_properties)

            self.btn_lst[-1].bind("<Enter>", self.hover)
            self.btn_lst[-1].bind("<Leave>", self.hover_leave)
            self.btn_lst[-1].bind("<Double-1>", self.on_double_click)
            self.btn_lst[-1].bind('<Button-3>', on_btn_2)
            # self.btn_lst[-1].bind('<Button-1>', self.on_click)


class FileExplorer(Frame):

    def __init__(self, root, controller):
        Frame.__init__(self, root)
        self.controller = controller
        self.current_dir = "/"

        # Image
        self.folder_icon = ImageTk.PhotoImage(Image.open(
            'Images\FolderIcon.png').resize((17, 18), Image.Resampling.LANCZOS))
        self.file_icon = ImageTk.PhotoImage(Image.open(
            'Images\FileIcon.png').resize((17, 22), Image.Resampling.LANCZOS))
        self.back_icon = ImageTk.PhotoImage(Image.open(
            'Images\GoBack.png').resize((24, 24), Image.Resampling.LANCZOS))

        # Directory treeview
        self.dir_treeview = ttk.Treeview(self)
        self.dir_treeview.pack(side=LEFT, fill=BOTH, expand=1, padx=5, pady=5)
        self.dir_treeview.heading(
            "#0", text='          '+vol_name[-2:]+'\\', anchor=W)
        self.dir_treeview.bind("<Double-1>", self.on_heading)
        # self.dir_treeview.bind("<Return>", self.show_info)
        # self.dir_treeview.bind("<ButtonRelease-1>", self.show_info)
        self.dir_treeview.bind("<<TreeviewSelect>>", self.show_info)

        self.scrollbar = Scrollbar(self)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.dir_treeview.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.dir_treeview.yview)

        self.heading_clicked = 0

        # Home button
        self.Home_Button = Button(
            self, image=self.back_icon, relief=GROOVE, command=self.go_back, compound=LEFT, background='#AED6F1', width=27, height=27).place(x=8, y=8)

        # INFORMATION WIDGETS
        self.info_frame = Frame(self, borderwidth=3, relief=RIDGE, width=600)
        self.info_frame.pack_propagate(0)
        self.info_frame.pack(side=RIGHT, fill=BOTH, expand=0, padx=5, pady=5)

        # 3 text areas
        self.text_area = Text(self.info_frame, font=(
            'Calibri', 11), bg='#F2F2F2', border=0, height=3, foreground='#34495E')
        self.text_area.config(spacing3=10, wrap='none')
        self.text_area.config(state=DISABLED)

        self.seperator = ttk.Separator(self.info_frame, orient='horizontal')

        self.text_area1 = Text(self.info_frame, font=(
            'Calibri', 11), bg='#F2F2F2', border=0, height=2, foreground='#34495E')
        self.text_area1.config(spacing3=10)
        self.text_area1.config(state=DISABLED)

        self.seperator1 = ttk.Separator(self.info_frame, orient='horizontal')

        self.text_area2 = Text(self.info_frame, font=(
            'Calibri', 11), bg='#F2F2F2', border=0, foreground='#34495E',)
        self.text_area2.config(spacing3=10)
        self.text_area2.config(state=DISABLED)

        # Display file tree
        self.update_dir_tree_recursion('', file_tree)
        # Set first item selected as defautl
        self.dir_treeview.focus_set()
        children = self.dir_treeview.get_children()
        if children:
            self.dir_treeview.focus(children[0])
            self.dir_treeview.selection_set(children[0])

    def go_back(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.controller.show_frame(VolumeListDisplay)

    def update_dir_tree_recursion(self, parent_node, parent_list):
        """
        Recursively updates the directory treeview with the subdirectories of a given path.
        """
        for i in parent_list:
            self.icon = ()
            if i['Flags'] & 0b100000:
                self.icon = self.file_icon
            if i['Flags'] & 0b010000:
                self.icon = self.folder_icon
            child_node = self.dir_treeview.insert(
                parent_node, END, text=' ' + i["Name"], iid=parent_node + '\\' + i["Name"], image=self.icon)

            if (i["Flags"] & 0b010000):
                self.update_dir_tree_recursion(child_node, i["lsFileFolder"])

    def open_children(self, parent):
        self.dir_treeview.item(parent, open=True)
        for child in self.dir_treeview.get_children(parent):
            self.open_children(child)

    def close_children(self, parent):
        self.dir_treeview.item(parent, open=False)
        for child in self.dir_treeview.get_children(parent):
            self.close_children(child)

    def on_heading(self, event):
        region = self.dir_treeview.identify("region", event.x, event.y)
        if region == "heading":
            if self.heading_clicked == 0:
                self.open_children('')
                self.heading_clicked = 1
            else:
                self.close_children('')
                self.heading_clicked = 0

    def show_info(self, event):

        selected_item_path = self.dir_treeview.selection()[0]
        info = FileTree(file_tree).get_file(selected_item_path)

        # TEXT AREA
        self.text_area.config(state=NORMAL)
        self.text_area.delete(1.0, END)
        self.text_area.insert(1.0, ' Name:\t\t' + info['Name'])
        self.text_area.insert(END, '\n' + ' Location:\t\t' + vol_name +
                              selected_item_path.replace(getFileName(selected_item_path), ''))
        self.text_area.insert(END, '\n' + ' Size:\t\t' + big_size_truncate(info['Size']) + ' (' +
                              str("{:,}".format(info['Size'])) + ' Bytes)')
        self.text_area.config(state=DISABLED)

        # TEXT AREA 1
        self.text_area1.config(state=NORMAL)
        self.text_area1.delete(1.0, END)
        self.text_area1.insert(1.0, ' Date Created:\t\t' +
                               info["Date Created"].strftime("%d %b, %Y, %H:%M:%S"))
        self.text_area1.insert(END, '\n' + ' Date Modified:\t\t' +
                               info["Date Modified"].strftime("%d %b, %Y, %H:%M:%S"))
        self.text_area1.config(state=DISABLED)

        # TEXT AREA 2
        self.text_area2.config(state=NORMAL)
        self.text_area2.delete(1.0, END)
        if info['Flags'] & 0b010000:
            self.text_area2.insert(1.0, ' Contains:\t\t' + str(
                info['NoFile']) + ' Files, ' + str(info['NoFolder']) + ' Folders' + '\n')
            self.text_area2.insert(END, ' Attributes:\t\t')
        else:
            self.text_area2.insert(1.0, ' Attributes:\t\t')

        ATB = ['READ_ONLY', 'HIDDEN', 'ARCHIVE']
        file_atb = info['Attributes']

        check = ()
        checkbox = ()

        for i in ATB:
            checkbox = Checkbutton(
                self.text_area2, text=i, variable=check, font=('Calibri', 11))
            if i in file_atb:
                checkbox.select()
            self.text_area2.window_create(END, window=checkbox)
            checkbox.configure(state=DISABLED)
            self.text_area2.insert(END, '\n\t\t')
        self.text_area2.config(state=DISABLED)

        self.text_area.pack(side=TOP, padx=20)
        self.seperator.pack(side=TOP, fill=X, padx=20)
        self.text_area1.pack(side=TOP, padx=20)
        self.seperator1.pack(side=TOP, fill=X, padx=20)
        self.text_area2.pack(side=TOP, padx=20)

        return 'break'


# MAIN
if __name__ == "__main__":
    app = App()
    app.mainloop()
