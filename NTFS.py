import re
from enum import Flag, auto
from datetime import datetime

# Định nghĩa lớp NTFSAttribute, kế thừa từ lớp Flag trong module enum.
# Lớp này đại diện cho các thuộc tính của một tập tin trong hệ thống tập tin NTFS của Windows.
class NTFSAttribute(Flag):
    READ_ONLY = auto()     # Tập tin chỉ cho phép đọc
    HIDDEN = auto()        # Tập tin được ẩn
    SYSTEM = auto()        # Tập tin hệ thống
    VOLLABLE = auto()      # Tập tin dùng để phục vụ truyền thông
    DIRECTORY = auto()     # Tập tin là một thư mục
    ARCHIVE = auto()       # Tập tin đã được sao lưu
    DEVICE = auto()        # Tập tin là một thiết bị
    NORMAL = auto()        # Tập tin bình thường
    TEMPORARY = auto()     # Tập tin tạm thời
    SPARSE_FILE = auto()   # Tập tin dạng sparse
    REPARSE_POINT = auto() # Tập tin dạng reparse point
    COMPRESSED = auto()    # Tập tin đã được nén
    OFFLINE = auto()       # Tập tin không được truy cập trực tiếp
    NOT_INDEXED = auto()   # Tập tin không được đánh chỉ mục
    ENCRYPTED = auto()     # Tập tin đã được mã hóa

# Định nghĩa hàm as_datetime()
# Hàm này nhận đầu vào là một timestamp và trả về một đối tượng datetime tương ứng với thời điểm được chỉ định bởi timestamp đó.
def as_datetime(timestamp):
    # Tính toán thời điểm tương ứng với timestamp bằng cách trừ đi 116444736000000000 (đây là số giây kể từ ngày 1 tháng 1 năm 1601 đến ngày 1 tháng 1 năm 1970, 
    # đây là một điểm chuẩn được sử dụng trong hệ thống tập tin NTFS của Windows) và sau đó chia cho 10000000 để chuyển đổi đơn vị từ nano giây sang giây.
    # Cuối cùng, hàm sử dụng module datetime để tạo ra đối tượng datetime tương ứng với thời điểm này và trả về đối tượng này.
    return datetime.fromtimestamp((timestamp - 116444736000000000) // 10000000)


class MFTRecord:
  def __init__(self, data) -> None: #Nhận đầu vào là dữ liệu của MFT, dùng để trích xuất thông tin về các tệp tin và thư mục bên trong hệ thống tệp NTFS.
    # Khởi tạo 
    self.raw_data = data
    
    # Lấy file id và flag
    self.file_id = int.from_bytes(self.raw_data[0x2C:0x30], byteorder='little')
    self.flag = self.raw_data[0x16]
    
    # Nếu là record đã bị xóa, raise exception để bỏ qua
    if self.flag == 0 or self.flag == 2: 
      raise Exception("Skip this record")
    
    # Lấy thông tin cơ bản 
    standard_info_start = int.from_bytes(self.raw_data[0x14:0x16], byteorder='little')
    standard_info_size = int.from_bytes(self.raw_data[standard_info_start + 4:standard_info_start + 8], byteorder='little')
    
    # Tạo dictionary để lưu thông tin
    self.standard_info = {}
    self.__parse_standard_info(standard_info_start)
    
    # Lên tên file hoặc tên thư mục
    file_name_start = standard_info_start + standard_info_size
    file_name_size = int.from_bytes(self.raw_data[file_name_start + 4:file_name_start + 8], byteorder='little')
    
    # Tạo dictionary để lưu tên
    self.file_name = {}
    self.__parse_file_name(file_name_start)
    
    # Lấy thông tin data
    data_start = file_name_start + file_name_size
    data_sig = self.raw_data[data_start:data_start + 4]
    
    # Nếu là thuộc tính non-resident (ngoài MFT) thì cập nhật vị trí start của data
    if data_sig[0] == 64:
      data_start += int.from_bytes(self.raw_data[data_start + 4:data_start + 8], byteorder='little')
    
    # Chuyển định dang data
    data_sig = self.raw_data[data_start:data_start + 4]
    self.data = {}
    if data_sig[0] == 128:
      self.__parse_data(data_start)
    elif data_sig[0] == 144:
      self.standard_info['flags'] |= NTFSAttribute.DIRECTORY
      self.data['size'] = 0
      self.data['resident'] = True
      
    # Tạo danh sách chứa các tệp tin và thư mục con
    self.childs: list[MFTRecord] = []

    # Xóa để giải phóng bộ nhớ
    del self.raw_data

  # Hàm kiểm tra thư mục
  def is_directory(self):
    return NTFSAttribute.DIRECTORY in self.standard_info['flags']

  # Hàm kiểm tra record này là active (nghĩa là không bị ẩn hoạc là system)
  def is_active_record(self):
    flags = self.standard_info['flags']
    if NTFSAttribute.SYSTEM in flags:
      return False
    return True
  
  # Hàm tìm record với tên
  def find_record(self, name: str):
    for record in self.childs:
      if record.file_name['long_name'] == name:
        return record
    return None
  
  # Hàm trả về danh sách active record
  def get_active_records(self) -> 'list[MFTRecord]':
    record_list: list[MFTRecord] = []
    for record in self.childs:
      if record.is_active_record():
        record_list.append(record)
    return record_list
  
  # Hàm chuyển định dạng data
  def __parse_data(self, start):
    # Kiểm tra nếu thuộc tính được lưu trong MFT hay ở ngoài
    self.data['resident'] = not bool(self.raw_data[start+0x8])
    if self.data['resident']:
      offset = int.from_bytes(self.raw_data[start + 0x14:start + 0x16], byteorder='little')
      # Lấy kích thước dự liệu và nội dung từ offset
      self.data['size'] = int.from_bytes(self.raw_data[start+0x10:start+0x14], byteorder='little')
      self.data['content'] = self.raw_data[start + offset:start + offset + self.data['size']]
    else:
      # Nếu thuộc tính không được lưu trong MFT thì phải lấy dữ liệu từ các cluster liên tiếp bên ngoài
      cluster_chain = self.raw_data[start + 0x40]
      offset = (cluster_chain & 0xF0) >> 4
      size = cluster_chain & 0x0F
      self.data['size'] = int.from_bytes(self.raw_data[start + 0x30: start + 0x38], byteorder='little')
      self.data['cluster_size'] = int.from_bytes(self.raw_data[start + 0x41: start + 0x41 + size], byteorder='little')
      self.data['cluster_offset'] =  int.from_bytes(self.raw_data[start + 0x41 + size: start + 0x41 + size + offset], byteorder='little')


  def __parse_file_name(self, start):
    # Đọc 4 byte đầu của record
    sig = int.from_bytes(self.raw_data[start:start + 4], byteorder='little')
    
    # Kiểm tra nếu không là tên file
    if sig != 0x30:
      raise Exception("Skip this record")
    
    # Lấy kích thước và offset của phần giữa
    size = int.from_bytes(self.raw_data[start + 0x10:start + 0x14], byteorder='little')
    offset = int.from_bytes(self.raw_data[start + 0x14: start + 0x16], byteorder='little')
    
    # Lấy thông tin phần giữa
    body = self.raw_data[start + offset: start + offset + size]
    
    # Lấy ra ID của cha và tên đầy đủ
    self.file_name["parent_id"] = int.from_bytes(body[:6], byteorder='little')
    name_length = body[64]
    self.file_name["long_name"] = body[66:66 + name_length * 2].decode('utf-16le')  # unicode

  def __parse_standard_info(self, start):
    # Đọc 4 byte đầu của record
    sig = int.from_bytes(self.raw_data[start:start + 4], byteorder='little')
    
    # Kiểm tra nếu không là thông tin chung
    if sig != 0x10:
      raise Exception("Something Wrong!")
    
    # Lấy offset của thông tin chung
    offset = int.from_bytes(self.raw_data[start + 20:start + 21], byteorder='little')
    
    # Tìm vị trí bắt đầu
    begin = start + offset
    
    # Lấy thời gian tạo, lần cuối chỉnh sửa và cờ (flag)
    self.standard_info["created_time"] = as_datetime(int.from_bytes(self.raw_data[begin:begin + 8], byteorder='little'))
    self.standard_info["last_modified_time"] = as_datetime(int.from_bytes(self.raw_data[begin + 8:begin + 16], byteorder='little'))
    self.standard_info["flags"] = NTFSAttribute(int.from_bytes(self.raw_data[begin + 32:begin + 36], byteorder='little') & 0xFFFF)

  def ListAttr(self):
    # Khởi tọa danh sách trống
    li = []
    # Kiểm tra cờ nào được bật, sau đó thêm thuộc tính đó vào danh sách
    if(NTFSAttribute.READ_ONLY in self.standard_info['flags']):
      li.append("READ_ONLY")
    if(NTFSAttribute.HIDDEN in self.standard_info['flags']):
      li.append("HIDDEN")
    if(NTFSAttribute.SYSTEM in self.standard_info['flags']):
      li.append("SYSTEM")
    if(NTFSAttribute.VOLLABLE in self.standard_info['flags']):
      li.append("VOLLABLE")
    if(NTFSAttribute.DIRECTORY in self.standard_info['flags']):
      li.append("DIRECTORY")
    if(NTFSAttribute.ARCHIVE in self.standard_info['flags']):
      li.append("ARCHIVE")
      
    # Trả về danh sách thuốc tính
    return li

class DirectoryTree:
  def __init__(self, nodes: 'list[MFTRecord]') -> None:
    # Khởi tạo cây thư mục từ MFTRecord
    self.root = None
    # Tạo dictionary để lưu thư mục dựa trên ID
    self.nodes_dict: dict[int, MFTRecord] = {}
    for node in nodes:
      self.nodes_dict[node.file_id] = node 

    # Thêm file/thư mục con vào danh sách con của thư mục cha
    for key in self.nodes_dict:
      parent_id = self.nodes_dict[key].file_name['parent_id']
      if parent_id in self.nodes_dict:
        self.nodes_dict[parent_id].childs.append(self.nodes_dict[key])
        
    # Tìm gốc
    for key in self.nodes_dict:
      parent_id = self.nodes_dict[key].file_name['parent_id']
      if parent_id == self.nodes_dict[key].file_id:
        self.root = self.nodes_dict[key]
        break
    
    self.current_dir = self.root  # Đặt thư mục hiện tại làm gốc

  def find_record(self, name: str):
    # Tìm file hoặc thư mục
    return self.current_dir.find_record(name)
  
  def get_parent_record(self, record: MFTRecord):
    # Trả về cha của record này
    return self.nodes_dict[record.file_name['parent_id']]

  def get_active_records(self) -> 'list[MFTRecord]':
    # Dùng để lấy danh sách active record từ thư mục này
    return self.current_dir.get_active_records()


class MFTFile:
  def __init__(self, data: bytes) -> None:
    self.raw_data = data                           
    self.info_offset = int.from_bytes(self.raw_data[0x14:0x16], byteorder='little')  # Lấy offset của attribute information
    self.info_len = int.from_bytes(self.raw_data[0x3C:0x40], byteorder='little')    # Lấy chiều dài của attribute information
    self.file_name_offset = self.info_offset + self.info_len    # Tính offset của file name attribute
    self.file_name_len = int.from_bytes(self.raw_data[0x9C:0xA0], byteorder='little')  # Lấy chiều dài của file name attribute
    self.data_offset = self.file_name_offset + self.file_name_len    # Tính offset của data attribute
    self.data_len = int.from_bytes(self.raw_data[0x104:0x108], byteorder='little')  # Lấy chiều dài của data attribute
    self.num_sector = (int.from_bytes(self.raw_data[0x118:0x120], byteorder='little') + 1) * 8  # Tính số sector của file
    del self.raw_data  


class NTFSVol:
  Information = [
    "OEM_ID",
    "Serial Number",
    "Bytes Per Sector",
    "Sectors Per Cluster", 
    "Reserved Sectors",
    "No. Sectors In Volume",
    "First Cluster of $MFT",
    "First Cluster of $MFTMirr",
    "MFT record size"
  ]
  def __init__(self, name: str) -> None:
    self.name = name 
    # Mở volume dưới dạng binary
    try:
      self.fd = open(r'\\.\%s' % self.name, 'rb')
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
      # Đọc phần boot sector
      self.BootSector_raw = self.fd.read(0x200)
      self.BootSector = {}
      self.__extract_BootSector()

      # Kiểm tra NTFS
      if self.BootSector["OEM_ID"] != b'NTFS    ':
        raise Exception("Not NTFS")
      # Định dạng lại thông tin cơ bản
      self.BootSector["OEM_ID"] = self.BootSector["OEM_ID"].decode()
      self.BootSector['Serial Number'] = hex(self.BootSector['Serial Number'] & 0xFFFFFFFF)[2:].upper()
      self.BootSector['Serial Number'] = self.BootSector['Serial Number'][:4] + "-" + self.BootSector['Serial Number'][4:]
      self.SC = self.BootSector["Sectors Per Cluster"]
      self.BS = self.BootSector["Bytes Per Sector"]
      self.record_size = self.BootSector["MFT record size"]
      self.mft_offset = self.BootSector['First Cluster of $MFT']
      
      # Đọc MFT và tạo danh sách MFTRecord
      self.fd.seek(self.mft_offset * self.SC * self.BS)
      self.mft_file = MFTFile(self.fd.read(self.record_size))
      mft_record: list[MFTRecord] = []
      for _ in range(2, self.mft_file.num_sector, 2):
        dat = self.fd.read(self.record_size)
        if dat[:4] == b"FILE":
          try:
            mft_record.append(MFTRecord(dat))
          except Exception as e:
            pass
      
      # Tạo cây thư mục từ danh sách MFTRecord
      self.dir_tree = DirectoryTree(mft_record)
    except Exception as e:
      print(f"[ERROR] {e}")
      exit()

  @staticmethod
  def check_ntfs(name: str):
    try:
      # Mở file dưới dạng binary và đọc 11 bytes
      with open(r'\\.\%s' % name, 'rb') as fd:
        oem_id = fd.read(0xB)[3:]
        # Kiểm tra nếu là NTFS
        if oem_id == b'NTFS    ':
          return True
        return False
    except Exception as e:
      print(f"[ERROR] {e}")
      exit()

  def __extract_BootSector(self):
    # Đọc các thông tin cần thiết 
    self.BootSector['OEM_ID'] = self.BootSector_raw[3:0xB]
    self.BootSector['Bytes Per Sector'] = int.from_bytes(self.BootSector_raw[0xB:0xD], byteorder='little')
    self.BootSector['Sectors Per Cluster'] = int.from_bytes(self.BootSector_raw[0xD:0xE], byteorder='little')
    self.BootSector['Reserved Sectors'] = int.from_bytes(self.BootSector_raw[0xE:0x10], byteorder='little')
    self.BootSector['No. Sectors In Volume'] = int.from_bytes(self.BootSector_raw[0x28:0x30], byteorder='little')
    self.BootSector['First Cluster of $MFT'] = int.from_bytes(self.BootSector_raw[0x30:0x38], byteorder='little')
    self.BootSector['First Cluster of $MFTMirr'] = int.from_bytes(self.BootSector_raw[0x38:0x40], byteorder='little')
    self.BootSector['Clusters Per File Record Segment'] = abs(int.from_bytes(self.BootSector_raw[0x40:0x41], byteorder='little', signed=True))
    self.BootSector['MFT record size'] = 2 ** abs(self.BootSector['Clusters Per File Record Segment'])
    self.BootSector['Serial Number'] = int.from_bytes(self.BootSector_raw[0x48:0x50], byteorder='little')
    self.BootSector['Signature'] = hex(int.from_bytes(self.BootSector_raw[0x1FE:0x200]) & 0xFFFFFFFF)[2:].upper()
  
  def getBootSector(self):
    return self.BootSector
  
  def visitFolder(self, name) -> MFTRecord: 
    # Kiểm tra tên thư mục
    if name == "":
      raise Exception("Directory name is required!")
    cur_dir = self.dir_tree.current_dir
    if name == "..":
      # Nếu thức hiện tại là gốc thì giữ nguyên
      cur_dir = self.dir_tree.get_parent_record(cur_dir)
      return cur_dir
    elif name == ".":
      return cur_dir
    # Tìm record của thư mục hiện tại
    record = cur_dir.find_record(name)
    if record is None:
      raise Exception("Directory not found!")
    if record.is_directory():
      cur_dir = record
    else:
      raise Exception("Not a directory")
    # Trả về record của thư mục
    return cur_dir

  def getAllRecords(self):
    try:
      record_list = self.dir_tree.get_active_records()
      ret = []
      for record in record_list:
        obj = {}
        obj["Flags"] = record.standard_info['flags'].value
        obj['Date Created'] = record.standard_info['created_time']
        obj["Date Modified"] = record.standard_info['last_modified_time']
        obj["Size"] = record.data['size']
        obj["Name"] = record.file_name['long_name']
        obj["Attributes"] = record.ListAttr()
        # Nếu record là thư mục rỗng, thêm các trường liên quan
        if(obj["Flags"] & 0b000000000010000):
            obj.update({"NoFile":0})
            obj.update({"NoFolder":0})
            obj.update({"lsFileFolder":[]})
        ret.append(obj)
      return ret
    except Exception as e:
      raise (e)

  def changeFolder(self, name=""):
    if name == "":
      raise Exception("Name to directory is required!")
    try:
      # Đến thư mục tiếp theo
      next_dir = self.visitFolder(name)
      self.dir_tree.current_dir = next_dir
    except Exception as e:
      raise (e)
  
  def ListElement(self):
    # Hàm lấy thông tin file và thư mục
    def FindFileFolder(entry):
      if entry["Flags"] & 0b100000:
        return entry
      self.changeFolder(entry["Name"])
      entries = self.getAllRecords()
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
      self.changeFolder("..")
      return entry

    lsFileFolder1 = []
    try:
      entries = self.getAllRecords()
      l = len(entries)
      for i in range(l):
        if entries[i]["Name"] in (".", ".."):
          continue
        lsFileFolder1.append(FindFileFolder(entries[i]))
    except Exception as e:
      print(f"[ERROR] {e}")
    return lsFileFolder1
  
  def __del__(self):
    # Hàm hủy
    if getattr(self, "fd", None):
      print("Closing Volume...")
      self.fd.close()
