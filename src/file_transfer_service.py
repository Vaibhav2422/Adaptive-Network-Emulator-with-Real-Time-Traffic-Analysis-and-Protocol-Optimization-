"""
File Transfer Service for the Adaptive Network Emulator.

This module implements file transfer functionality with segmentation for large files
and integrity verification using checksums.

Validates: Requirements 2.1, 2.2, 2.3, 2.5
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
import hashlib
import os
import time


@dataclass
class FileSegment:
    """
    Represents a segment of a file being transferred.
    
    Attributes:
        file_id: Unique file transfer identifier
        segment_num: Segment number (0-indexed)
        total_segments: Total number of segments in the file
        data: Segment data
        checksum: Checksum for this segment
    """
    file_id: str
    segment_num: int
    total_segments: int
    data: bytes
    checksum: str
    
    def verify_checksum(self) -> bool:
        """Verify segment checksum."""
        computed = hashlib.sha256(self.data).hexdigest()
        return computed == self.checksum
    
    @staticmethod
    def compute_checksum(data: bytes) -> str:
        """Compute SHA-256 checksum for data."""
        return hashlib.sha256(data).hexdigest()


@dataclass
class FileTransferState:
    """
    Tracks the state of an ongoing file transfer.
    
    Attributes:
        file_id: Unique file transfer identifier
        filename: Original filename
        total_size: Total file size in bytes
        total_segments: Total number of segments
        received_segments: Dictionary of received segments
        file_checksum: Checksum of the complete file
        started_at: Transfer start timestamp
        completed_at: Transfer completion timestamp
    """
    file_id: str
    filename: str
    total_size: int
    total_segments: int
    received_segments: Dict[int, FileSegment] = field(default_factory=dict)
    file_checksum: str = ""
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    
    def is_complete(self) -> bool:
        """Check if all segments have been received."""
        return len(self.received_segments) == self.total_segments
    
    def get_progress(self) -> float:
        """Get transfer progress as a percentage (0.0 to 1.0)."""
        if self.total_segments == 0:
            return 0.0
        return len(self.received_segments) / self.total_segments
    
    def add_segment(self, segment: FileSegment) -> bool:
        """
        Add a received segment.
        
        Args:
            segment: File segment to add
        
        Returns:
            True if segment was added successfully
        """
        # Verify segment belongs to this transfer
        if segment.file_id != self.file_id:
            return False
        
        # Verify segment number is valid
        if segment.segment_num < 0 or segment.segment_num >= self.total_segments:
            return False
        
        # Verify segment checksum
        if not segment.verify_checksum():
            return False
        
        # Add segment
        self.received_segments[segment.segment_num] = segment
        
        # Check if transfer is complete
        if self.is_complete():
            self.completed_at = time.time()
        
        return True
    
    def reassemble_file(self) -> Optional[bytes]:
        """
        Reassemble the complete file from segments.
        
        Returns:
            Complete file data, or None if transfer is incomplete
        """
        if not self.is_complete():
            return None
        
        # Sort segments by segment number
        sorted_segments = sorted(
            self.received_segments.values(),
            key=lambda s: s.segment_num
        )
        
        # Concatenate segment data
        file_data = b"".join(segment.data for segment in sorted_segments)
        
        return file_data


@dataclass
class FileTransferService:
    """
    File transfer service with segmentation and integrity verification.
    
    Provides functionality to send and receive files over the network,
    with support for large file segmentation and checksum verification.
    
    Attributes:
        segment_size: Maximum size of each file segment in bytes
        active_transfers: Dictionary of active file transfers
        completed_transfers: Dictionary of completed file transfers
    
    Validates: Requirements 2.1, 2.2, 2.3, 2.5
    """
    segment_size: int = 1024  # 1 KB default segment size
    active_transfers: Dict[str, FileTransferState] = field(default_factory=dict)
    completed_transfers: Dict[str, FileTransferState] = field(default_factory=dict)
    
    def send_file(
        self,
        file_path: str,
        dest_node: str,
        protocol: str,
        send_callback
    ) -> Optional[str]:
        """
        Send a file to a destination node.
        
        Args:
            file_path: Path to the file to send
            dest_node: Destination node identifier
            protocol: Protocol to use (TCP or UDP)
            send_callback: Callback function to send segments
        
        Returns:
            File transfer ID if successful, None otherwise
        
        Validates: Requirements 2.2 (TCP file transfer), 2.3 (UDP file transfer)
        """
        # Check if file exists
        if not os.path.exists(file_path):
            return None
        
        # Read file data
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Generate file ID
        file_id = hashlib.sha256(
            f"{file_path}{dest_node}{time.time()}".encode()
        ).hexdigest()[:16]
        
        # Compute file checksum
        file_checksum = hashlib.sha256(file_data).hexdigest()
        
        # Segment the file
        segments = self._segment_file(file_id, file_data)
        
        # Create transfer state
        transfer_state = FileTransferState(
            file_id=file_id,
            filename=os.path.basename(file_path),
            total_size=len(file_data),
            total_segments=len(segments),
            file_checksum=file_checksum
        )
        
        self.active_transfers[file_id] = transfer_state
        
        # Send segments
        for segment in segments:
            # Serialize segment for transmission
            segment_data = self._serialize_segment(segment)
            
            # Send via callback
            send_callback(
                dest=dest_node,
                data=segment_data,
                protocol=protocol,
                file_id=file_id
            )
        
        # Move to completed transfers
        self.completed_transfers[file_id] = transfer_state
        del self.active_transfers[file_id]
        
        return file_id
    
    def receive_segment(self, segment_data: bytes) -> bool:
        """
        Receive a file segment.
        
        Args:
            segment_data: Serialized segment data
        
        Returns:
            True if segment was received successfully
        """
        # Deserialize segment
        segment = self._deserialize_segment(segment_data)
        if not segment:
            return False
        
        # Get or create transfer state
        if segment.file_id not in self.active_transfers:
            # Create new transfer state
            transfer_state = FileTransferState(
                file_id=segment.file_id,
                filename="received_file",
                total_size=0,  # Unknown until complete
                total_segments=segment.total_segments
            )
            self.active_transfers[segment.file_id] = transfer_state
        
        transfer_state = self.active_transfers[segment.file_id]
        
        # Add segment to transfer
        success = transfer_state.add_segment(segment)
        
        # If transfer is complete, move to completed transfers
        if transfer_state.is_complete():
            self.completed_transfers[segment.file_id] = transfer_state
            del self.active_transfers[segment.file_id]
        
        return success
    
    def get_received_file(self, file_id: str) -> Optional[bytes]:
        """
        Get a received file by ID.
        
        Args:
            file_id: File transfer identifier
        
        Returns:
            Complete file data, or None if transfer is incomplete
        
        Validates: Requirement 2.5 (file integrity verification)
        """
        transfer_state = self.completed_transfers.get(file_id)
        if not transfer_state:
            return None
        
        # Reassemble file
        file_data = transfer_state.reassemble_file()
        if not file_data:
            return None
        
        # Verify file integrity
        if transfer_state.file_checksum:
            computed_checksum = hashlib.sha256(file_data).hexdigest()
            if computed_checksum != transfer_state.file_checksum:
                return None  # Integrity check failed
        
        return file_data
    
    def verify_file_integrity(self, file_id: str, expected_checksum: str) -> bool:
        """
        Verify the integrity of a received file.
        
        Args:
            file_id: File transfer identifier
            expected_checksum: Expected file checksum
        
        Returns:
            True if file integrity is verified
        
        Validates: Requirement 2.5 (file integrity verification)
        """
        file_data = self.get_received_file(file_id)
        if not file_data:
            return False
        
        computed_checksum = hashlib.sha256(file_data).hexdigest()
        return computed_checksum == expected_checksum
    
    def _segment_file(self, file_id: str, file_data: bytes) -> List[FileSegment]:
        """
        Segment a file into chunks.
        
        Args:
            file_id: File transfer identifier
            file_data: Complete file data
        
        Returns:
            List of file segments
        
        Validates: Requirement 2.2 (file segmentation for large files)
        """
        segments = []
        total_segments = (len(file_data) + self.segment_size - 1) // self.segment_size
        
        for i in range(total_segments):
            start = i * self.segment_size
            end = min(start + self.segment_size, len(file_data))
            segment_data = file_data[start:end]
            
            segment = FileSegment(
                file_id=file_id,
                segment_num=i,
                total_segments=total_segments,
                data=segment_data,
                checksum=FileSegment.compute_checksum(segment_data)
            )
            
            segments.append(segment)
        
        return segments
    
    def _serialize_segment(self, segment: FileSegment) -> bytes:
        """Serialize a file segment for transmission."""
        # Simple serialization format:
        # file_id (16 bytes) | segment_num (4 bytes) | total_segments (4 bytes) | 
        # checksum (64 bytes) | data_length (4 bytes) | data
        
        file_id_bytes = segment.file_id.encode('utf-8').ljust(16, b'\x00')
        segment_num_bytes = segment.segment_num.to_bytes(4, 'big')
        total_segments_bytes = segment.total_segments.to_bytes(4, 'big')
        checksum_bytes = segment.checksum.encode('utf-8').ljust(64, b'\x00')
        data_length_bytes = len(segment.data).to_bytes(4, 'big')
        
        return (
            file_id_bytes +
            segment_num_bytes +
            total_segments_bytes +
            checksum_bytes +
            data_length_bytes +
            segment.data
        )
    
    def _deserialize_segment(self, data: bytes) -> Optional[FileSegment]:
        """Deserialize a file segment from transmission data."""
        if len(data) < 92:  # Minimum header size
            return None
        
        try:
            # Parse header
            file_id = data[0:16].rstrip(b'\x00').decode('utf-8')
            segment_num = int.from_bytes(data[16:20], 'big')
            total_segments = int.from_bytes(data[20:24], 'big')
            checksum = data[24:88].rstrip(b'\x00').decode('utf-8')
            data_length = int.from_bytes(data[88:92], 'big')
            
            # Parse data
            segment_data = data[92:92+data_length]
            
            return FileSegment(
                file_id=file_id,
                segment_num=segment_num,
                total_segments=total_segments,
                data=segment_data,
                checksum=checksum
            )
        except Exception:
            return None


@dataclass
class MessageService:
    """
    Message service for text message transmission.
    
    Provides simple text message sending and receiving functionality.
    
    Validates: Requirement 2.1 (text message transmission)
    """
    
    @staticmethod
    def encode_message(message: str) -> bytes:
        """
        Encode a text message for transmission.
        
        Args:
            message: Text message
        
        Returns:
            Encoded message bytes
        """
        return message.encode('utf-8')
    
    @staticmethod
    def decode_message(data: bytes) -> str:
        """
        Decode a received message.
        
        Args:
            data: Encoded message bytes
        
        Returns:
            Decoded text message
        """
        return data.decode('utf-8')
    
    @staticmethod
    def create_message_packet(sender: str, message: str) -> bytes:
        """
        Create a message packet with sender information.
        
        Args:
            sender: Sender identifier
            message: Text message
        
        Returns:
            Message packet bytes
        """
        # Simple format: sender_length (2 bytes) | sender | message
        sender_bytes = sender.encode('utf-8')
        sender_length = len(sender_bytes).to_bytes(2, 'big')
        message_bytes = message.encode('utf-8')
        
        return sender_length + sender_bytes + message_bytes
    
    @staticmethod
    def parse_message_packet(data: bytes) -> tuple[str, str]:
        """
        Parse a message packet.
        
        Args:
            data: Message packet bytes
        
        Returns:
            Tuple of (sender, message)
        """
        if len(data) < 2:
            return ("", "")
        
        sender_length = int.from_bytes(data[0:2], 'big')
        sender = data[2:2+sender_length].decode('utf-8')
        message = data[2+sender_length:].decode('utf-8')
        
        return (sender, message)
