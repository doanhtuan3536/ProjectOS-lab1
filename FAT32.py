from enum import Flag, auto
from datetime import datetime
from itertools import chain
class Attribute(Flag):
    READ_ONLY = auto()
    HIDDEN = auto()
    SYSTEM = auto()
    VOLLABLE = auto()
    DIRECTORY = auto()
    ARCHIVE = auto()

#class Fat lưu data, các phần tử của một bảng fat
class FAT:
  def __init__(self, data) -> None:
    self.raw_data = data
    self.elements = []
    l = len(self.raw_data)
    for i in range(0, l, 4):
      self.elements.append(int.from_bytes(self.raw_data[i:i + 4], byteorder='little'))
  #lấy ra các cluster từ cluster bắt đầu của folder hay rdet
  def getAllCluster(self, index: int) -> 'list[int]':
    ListIndexCluster = []
    while True:
      ListIndexCluster.append(index)
      index = self.elements[index]
      if index == 0x0FFFFFFF or index == 0x0FFFFFF7:
        break
    return ListIndexCluster

class RDETentry: 
  def __init__(self, data) -> None:
    self.raw_data = data
    self.flag = data[0xB:0xC]
    self.is_subentry: bool = False
    self.is_deleted: bool = False
    self.is_empty: bool = False
    self.is_label: bool = False
    self.attr = Attribute(0)
    self.size = 0
    self.date_created = 0
    self.date_updated = 0
    self.ext = b""
    self.long_name = ""
    if self.flag == b'\x0f':
      self.is_subentry = True

    if not self.is_subentry: 
      self.name = self.raw_data[:0x8]
      self.ext = self.raw_data[0x8:0xB]
      if self.name[:1] == b'\xe5':# nếu là entry của file/ folder đã xóa
        self.is_deleted = True
      if self.name[:1] == b'\x00':#nếu là entry trống
        self.is_empty = True
        self.name = ""
        return
      
      self.attr = Attribute(int.from_bytes(self.flag, byteorder='little'))
      if Attribute.VOLLABLE in self.attr:
        self.is_label = True
        return
      self.time_created_raw = int.from_bytes(self.raw_data[0xD:0x10], byteorder='little')
      self.date_created_raw = int.from_bytes(self.raw_data[0x10:0x12], byteorder='little')
      self.time_updated_raw = int.from_bytes(self.raw_data[0x16:0x18], byteorder='little')
      self.date_updated_raw = int.from_bytes(self.raw_data[0x18:0x1A], byteorder='little')

      h = (self.time_created_raw & 0b111110000000000000000000) >> 19
      m = (self.time_created_raw & 0b000001111110000000000000) >> 13
      s = (self.time_created_raw & 0b000000000001111110000000) >> 7
      ms =(self.time_created_raw & 0b000000000000000001111111)
      year = 1980 + ((self.date_created_raw & 0b1111111000000000) >> 9)
      mon = (self.date_created_raw & 0b0000000111100000) >> 5
      day = self.date_created_raw & 0b0000000000011111

      self.date_created = datetime(year, mon, day, h, m, s, ms)

      h = (self.time_updated_raw & 0b1111100000000000) >> 11
      m = (self.time_updated_raw & 0b0000011111100000) >> 5
      s = (self.time_updated_raw & 0b0000000000011111) * 2
      year = 1980 + ((self.date_updated_raw & 0b1111111000000000) >> 9)
      mon = (self.date_updated_raw & 0b0000000111100000) >> 5
      day = self.date_updated_raw & 0b0000000000011111

      self.date_updated = datetime(year, mon, day, h, m, s)
      self.start_cluster = int.from_bytes(self.raw_data[0x14:0x16][::-1] + self.raw_data[0x1A:0x1C][::-1], byteorder='big') #tìm cluster bắt đầu của entry này, 2 byte cao ở 14 và 2 byte thấp ở 1A, đảo ngược lại rồi + cho nhau
      self.size = int.from_bytes(self.raw_data[0x1C:0x20], byteorder='little')

    else:
      self.index = self.raw_data[0]
      self.name = b""
      for i in chain(range(0x1, 0xB), range(0xE, 0x1A), range(0x1C, 0x20)):
        self.name += int.to_bytes(self.raw_data[i], 1, byteorder='little') #convert to bytes string
        if self.name.endswith(b"\xff\xff"):
          self.name = self.name[:-2]
          break
      self.name = self.name.decode('utf-16le').strip('\x00')

  #hàm kiểm tra có phải entry chính không
  def isMainEntry(self) -> bool:
    return not (self.is_empty or self.is_subentry or self.is_deleted or self.is_label or Attribute.SYSTEM in self.attr)
  
  #hàm kiểm tra có phải thư mục không
  def isDirectory(self) -> bool:
    return Attribute.DIRECTORY in self.attr
  
  #hàm trả về các thuộc tính của một file, folder
  def ListAttr(self):
    li = []
    if(Attribute.READ_ONLY in self.attr):
      li.append("READ_ONLY")
    if(Attribute.HIDDEN in self.attr):
      li.append("HIDDEN")
    if(Attribute.SYSTEM in self.attr):
      li.append("SYSTEM")
    if(Attribute.VOLLABLE in self.attr):
      li.append("VOLLABLE")
    if(Attribute.DIRECTORY in self.attr):
      li.append("DIRECTORY")
    if(Attribute.ARCHIVE in self.attr):
      li.append("ARCHIVE")
    return li

class RDET:
  def __init__(self, data: bytes) -> None:
    self.raw_data: bytes = data
    self.entries: list[RDETentry] = []
    long_name = ""
    l = len(data)
    for i in range(0, l, 32):
      self.entries.append(RDETentry(self.raw_data[i: i + 32])) #cứ lấy 32 bytes từ vùng data của rdet, phân tích entry đó và lưu vào danh sách
      #nếu entry đó đã xóa hoặc trống
      if self.entries[-1].is_empty or self.entries[-1].is_deleted:
        long_name = ""
        continue
      #nếu là entry phụ
      if self.entries[-1].is_subentry:
        long_name = self.entries[-1].name + long_name#lấy name của entry phụ này + với name của entry phụ trước đó
        continue
      #nếu là entry chính
      if long_name != "": #entry chính có các entr phụ
        self.entries[-1].long_name = long_name
      else:#entry chính ko có entry phụ
        extend = self.entries[-1].ext.strip().decode()
        if extend == "":#nếu là thư mục
          self.entries[-1].long_name = self.entries[-1].name.strip().decode()
        else:#nếu là tập tin
          self.entries[-1].long_name = self.entries[-1].name.strip().decode() + "." + extend
      long_name = ""
#biến name của entry chỉ để lưu name của các entry phụ, hoặc các entry của thư mục, tập tin ko có entry phụ
#biến long_name là lưu tên chính

#lấy tất cả các entry chính ra
  def getMainEntries(self) -> 'list[RDETentry]':
    entry_list = []
    for i in range(len(self.entries)):
      if self.entries[i].isMainEntry():
        entry_list.append(self.entries[i])
    return entry_list

  def findEntry(self, name) -> RDETentry:
    for i in range(len(self.entries)):
      if self.entries[i].isMainEntry() and self.entries[i].long_name.lower() == name.lower():
        return self.entries[i]
    return None

class FAT32Vol:
  
  def __init__(self, name: str) -> None:
    self.name = name
    try:
      self.fd = open(r'\\.\%s' % self.name, 'rb') #đọc tất cả dữ liệu nhị phân của ổ đĩa với tên đã truyền vào
    except FileNotFoundError:
      print(f"[ERROR] No volume named {name}")
      exit()
    except PermissionError:
      print("[ERROR] Permission denied, try again as admin/root")
      exit()
    except Exception as e:
      print(e)
      print("[ERROR] Unknown error occurred")
      exit() 
    
    try:
      self.boot_sector_data = self.fd.read(0x200) #đọc 512 bytes đầu tiên để bắt đầu phân tích dữ liệu của ổ đĩa vì đây data của boot sector
      self.boot_sector = {}
      self.ExtractBootSector()# phân tích ổ đĩa ở bootsector
      if self.boot_sector["FAT Name"] != b"FAT32   ":
        raise Exception("Not FAT32")
      #lưu các thông tin cần thiết
      self.boot_sector["FAT Name"] = self.boot_sector["FAT Name"].decode()
      self.SB = self.boot_sector['Reserved Sectors']
      self.SF = self.boot_sector["Sectors Per FAT"]
      self.NF = self.boot_sector["No of FAT"]
      self.SC = self.boot_sector["Sectors Per Cluster"]
      self.BS = self.boot_sector["Bytes Per Sector"]
      self.boot_sector_reserved_raw = self.fd.read(self.BS * (self.SB - 1))
      
      #Lấy data bảng fat
      FAT_size = self.BS * self.SF
      self.FAT: list[FAT] = []
      for _ in range(self.NF):
        self.FAT.append(FAT(self.fd.read(FAT_size)))
      #det sẽ là dictionary lưu lại list entry của tất thư mục có trong ổ đĩa
      #rdet sẽ lưu giữ list entry của thư mục hiện tại đang ở hoặc là list entry của rdet
      self.DET = {}
      start = self.boot_sector["Starting Cluster of RDET"]
      self.DET[start] = RDET(self.getAllClusterData(start))
      self.RDET = self.DET[start]
    except Exception as e:
      print(f"[ERROR] {e}")
      exit()
  
  @staticmethod
  def CheckFat32(name: str):
    try:
      with open(r'\\.\%s' % name, 'rb') as fd: #mở dữ liệu nhị phân ổ đĩa
        fd.read(1)
        fd.seek(0x52)#di chuyển con trỏ tới offset 0x52
        fat_name = fd.read(8)#đọc 8 bytes
        if fat_name == b"FAT32   ":
          return True
        return False
    except Exception as e:
      print(f"[ERROR] {e}")
      exit()
#phân tích boot sector
  def ExtractBootSector(self):
    self.boot_sector['Bytes Per Sector'] = int.from_bytes(self.boot_sector_data[0xB:0xD], byteorder='little')# lấy từ byte thứ 11(OB) đến byte thứ 12(OC) của boot sector raw
    self.boot_sector['Sectors Per Cluster'] = int.from_bytes(self.boot_sector_data[0xD:0xE], byteorder='little')
    self.boot_sector['Reserved Sectors'] = int.from_bytes(self.boot_sector_data[0xE:0x10], byteorder='little')
    self.boot_sector['No of FAT'] = int.from_bytes(self.boot_sector_data[0x10:0x11], byteorder='little')
    self.boot_sector['No Sectors In Volume'] = int.from_bytes(self.boot_sector_data[0x20:0x24], byteorder='little')
    self.boot_sector['Sectors Per FAT'] = int.from_bytes(self.boot_sector_data[0x24:0x28], byteorder='little')
    self.boot_sector['Starting Cluster of RDET'] = int.from_bytes(self.boot_sector_data[0x2C:0x30], byteorder='little')
    self.boot_sector['FAT Name'] = self.boot_sector_data[0x52:0x5A]
    self.boot_sector['Starting Sector of Data'] = self.boot_sector['Reserved Sectors'] + self.boot_sector['No of FAT'] * self.boot_sector['Sectors Per FAT']

  def getBootSector(self):
    return self.boot_sector

#thứ tự sector bắt đầu của 1 cluster
  def ThSectorOfCluster(self, index):
    return self.SB + self.SF * self.NF + (index - 2) * self.SC

  
  def ListEntryOfFolder(self, name = "") -> RDET:#lấy ra danh sách entries của một folder với tên của folder đó được truyền vào
    if name == "":
      raise Exception("Directory name is required!")
    Currentdet = self.RDET
    entry = Currentdet.findEntry(name) #tìm thư mục có tên name trong danh sách các entry của thư mục mà self.RDET giữ
    if entry is None:
      raise Exception("Directory not found!")
    if entry.isDirectory():
      if entry.start_cluster == 0:
        Currentdet = self.DET[self.boot_sector["Starting Cluster of RDET"]]
      elif entry.start_cluster in self.DET:#đây là khi muốn quay về thư mục cha
        Currentdet = self.DET[entry.start_cluster]
      else:
        self.DET[entry.start_cluster] = RDET(self.getAllClusterData(entry.start_cluster)) # lưu lại các danh sách entry của từng folder con và
        #Rdet để khi mà quay lại thư muc cha như ".." thì ko cần phải đi tìm các cluster data nữa
        Currentdet = self.DET[entry.start_cluster]
    else:
        raise Exception("Not a directory")
    return Currentdet
  
  def getElementOfFolder(self): #lấy ra các file/folder trong folder cha
    try:
      ListEntries = self.RDET.getMainEntries() #trả về các entries phù hợp, entries chính
      ret = []
      for entry in ListEntries:#duyệt qua các entries trong rdet (đã có đầy đủ thông tin các entry đó)
        en = {}
        en["Date Created"] = entry.date_created
        en["Flags"] = entry.attr.value
        en["Attributes"] = entry.ListAttr()
        en["Date Modified"] = entry.date_updated
        en["Size"] = entry.size
        en["Name"] = entry.long_name
        if(entry.isDirectory()):
            en.update({"NoFile":0})
            en.update({"NoFolder":0})
            en.update({"lsFileFolder":[]})
        ret.append(en)
      return ret
    except Exception as e:
      raise(e)
    
#đổi sang danh sách entry của thư mục khác
  def changeListEntry(self, name=""):
    if name == "":
      raise Exception("Name directory is required!")
    try:
      Currentdet = self.ListEntryOfFolder(name)
      self.RDET = Currentdet
    except Exception as e:
      raise(e)

#lấy tất cả cluster data của 1 thư mục hay là của rdet
  def getAllClusterData(self, cluster_index):
    ListIndex = self.FAT[0].getAllCluster(cluster_index)#tìm tất cả các index cluster mà folder chiếm giữ
    data = b""
    for i in ListIndex:
      ThSectorOfCluster = self.ThSectorOfCluster(i)
      self.fd.seek(ThSectorOfCluster * self.BS)
      data += self.fd.read(self.SC * self.BS)
    return data

#hàm trả về danh sách toàn bộ thông tin các file/ thư mục trong volumn
  def ListElement(self):
    def FindFileFolder(entry):
      #nếu là file bình thường thì return về để thêm vào list
      if entry["Flags"] & 0b100000:
        return entry
      #nếu là thư mục thì tìm thêm các file/folder nằm trong thư mục này, sau đó return về bỏ vào danh sách
      self.changeListEntry(entry["Name"]) # chuyển sang list entry của thư mục đó
      entries = self.getElementOfFolder()# lấy ra các entry thư mục đó
      l = len(entries) 
      for i in range(l):
        if entries[i]["Name"] in (".", ".."):
          continue
        entry["lsFileFolder"].append(FindFileFolder(entries[i]))
        if entries[i]["Flags"] & 0b100000:
          entry["NoFile"]+=1
        elif entries[i]["Flags"] & 0b010000:
          entry["NoFolder"]+= entries[i]["NoFolder"]+1
          entry["NoFile"]+= entries[i]["NoFile"]
        entry["Size"]+=entries[i]["Size"]
      self.changeListEntry("..")#thay đổi self.RDET về list entry của thư mục hiện tại
      return entry

    lsFileFolder1 = []
    try:
      entries = self.getElementOfFolder()# Lấy ra các entry của rdet để lấy ra các file/ folder con trực tiếp của ổ đĩa
      l = len(entries)
      for i in range(l):
        if entries[i]["Name"] in (".", ".."):
          continue
        lsFileFolder1.append(FindFileFolder(entries[i]))#thêm các file hoặc thư mục vào danh sách
    except Exception as e:
      print(f"[ERROR] {e}")
    return lsFileFolder1 #trả về danh sách

  def __del__(self):
    if getattr(self, "fd", None):
      print("Closing Volume...")
      self.fd.close()