"""
Discrete event simulation engine for the Adaptive Network Emulator.
Provides priority queue-based event scheduling with configurable simulation clock.
"""
import heapq
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, List
from enum import Enum
import logging


class EventType(Enum):
    """Types of events in the simulation."""
    PACKET_ARRIVAL = "packet_arrival"
    TIMER_EXPIRATION = "timer_expiration"
    ACK_RECEIPT = "ack_receipt"
    FRAME_TRANSMISSION = "frame_transmission"
    COLLISION = "collision"
    ROUTE_UPDATE = "route_update"
    OPTIMIZATION_TRIGGER = "optimization_trigger"


@dataclass(order=True)
class Event:
    """
    Represents a discrete event in the simulation.
    Events are ordered by scheduled_time for priority queue.
    """
    scheduled_time: float  # Simulation time when event should occur
    event_type: EventType = field(compare=False)
    handler: Callable = field(compare=False)
    data: Any = field(default=None, compare=False)
    event_id: int = field(default=0, compare=False)
    
    def __repr__(self) -> str:
        return f"Event(time={self.scheduled_time:.6f}, type={self.event_type.value}, id={self.event_id})"


class SimulationClock:
    """
    Manages simulation time with configurable speed.
    Supports real-time, fast-forward, and step-by-step execution.
    """
    
    def __init__(self, speed: float = 1.0):
        """
        Initialize simulation clock.
        
        Args:
            speed: Simulation speed multiplier (1.0 = real-time, >1.0 = fast-forward)
        """
        self.speed = speed
        self.sim_time = 0.0  # Current simulation time
        self.real_start_time = time.time()  # Real-world start time
        self.paused = False
        self.pause_time = 0.0
    
    def advance(self, delta: float) -> None:
        """
        Advance simulation time by delta.
        
        Args:
            delta: Time increment in simulation seconds
        """
        if not self.paused:
            self.sim_time += delta
    
    def set_time(self, new_time: float) -> None:
        """Set simulation time to a specific value."""
        self.sim_time = new_time
    
    def get_time(self) -> float:
        """Get current simulation time."""
        return self.sim_time
    
    def pause(self) -> None:
        """Pause the simulation clock."""
        if not self.paused:
            self.paused = True
            self.pause_time = time.time()
    
    def resume(self) -> None:
        """Resume the simulation clock."""
        if self.paused:
            self.paused = False
            pause_duration = time.time() - self.pause_time
            self.real_start_time += pause_duration
    
    def wait_until(self, target_time: float) -> None:
        """
        Wait in real-time until simulation reaches target time.
        Respects simulation speed setting.
        
        Args:
            target_time: Target simulation time
        """
        if self.paused or self.speed == 0:
            return
        
        time_delta = target_time - self.sim_time
        if time_delta > 0:
            real_wait = time_delta / self.speed
            time.sleep(real_wait)


class EventQueue:
    """
    Priority queue-based discrete event simulation engine.
    Manages event scheduling, execution, and tracing.
    """
    
    def __init__(self, clock: Optional[SimulationClock] = None,
                 enable_tracing: bool = False):
        """
        Initialize event queue.
        
        Args:
            clock: Simulation clock (creates default if None)
            enable_tracing: Enable event tracing for debugging
        """
        self.clock = clock or SimulationClock()
        self.queue: List[Event] = []
        self.event_counter = 0
        self.enable_tracing = enable_tracing
        self.event_trace: List[Event] = []
        self.logger = logging.getLogger("emulator.event_queue")
    
    def schedule(self, delay: float, event_type: EventType,
                handler: Callable, data: Any = None) -> int:
        """
        Schedule an event to occur after a delay.
        
        Args:
            delay: Delay in simulation time units
            event_type: Type of event
            handler: Callback function to execute
            data: Optional data to pass to handler
        
        Returns:
            Event ID
        """
        scheduled_time = self.clock.get_time() + delay
        event_id = self.event_counter
        self.event_counter += 1
        
        event = Event(
            scheduled_time=scheduled_time,
            event_type=event_type,
            handler=handler,
            data=data,
            event_id=event_id
        )
        
        heapq.heappush(self.queue, event)
        
        if self.enable_tracing:
            self.logger.debug(f"Scheduled {event}")
        
        return event_id
    
    def schedule_at(self, time: float, event_type: EventType,
                   handler: Callable, data: Any = None) -> int:
        """
        Schedule an event to occur at a specific simulation time.
        
        Args:
            time: Absolute simulation time
            event_type: Type of event
            handler: Callback function to execute
            data: Optional data to pass to handler
        
        Returns:
            Event ID
        """
        event_id = self.event_counter
        self.event_counter += 1
        
        event = Event(
            scheduled_time=time,
            event_type=event_type,
            handler=handler,
            data=data,
            event_id=event_id
        )
        
        heapq.heappush(self.queue, event)
        
        if self.enable_tracing:
            self.logger.debug(f"Scheduled {event}")
        
        return event_id
    
    def cancel(self, event_id: int) -> bool:
        """
        Cancel a scheduled event.
        
        Args:
            event_id: ID of event to cancel
        
        Returns:
            True if event was found and cancelled
        """
        for i, event in enumerate(self.queue):
            if event.event_id == event_id:
                self.queue.pop(i)
                heapq.heapify(self.queue)
                if self.enable_tracing:
                    self.logger.debug(f"Cancelled event {event_id}")
                return True
        return False
    
    def process_next(self) -> bool:
        """
        Process the next event in the queue.
        
        Returns:
            True if an event was processed, False if queue is empty
        """
        if not self.queue:
            return False
        
        event = heapq.heappop(self.queue)
        
        # Advance simulation clock to event time
        self.clock.set_time(event.scheduled_time)
        
        # Wait in real-time if needed
        if self.clock.speed > 0:
            self.clock.wait_until(event.scheduled_time)
        
        if self.enable_tracing:
            self.logger.debug(f"Processing {event}")
            self.event_trace.append(event)
        
        # Execute event handler
        try:
            if event.data is not None:
                event.handler(event.data)
            else:
                event.handler()
        except Exception as e:
            self.logger.error(f"Error processing {event}: {e}", exc_info=True)
        
        return True
    
    def run(self, until: Optional[float] = None, max_events: Optional[int] = None) -> None:
        """
        Run the simulation until a condition is met.
        
        Args:
            until: Stop when simulation time reaches this value
            max_events: Stop after processing this many events
        """
        events_processed = 0
        
        while self.queue:
            # Check stopping conditions
            if until is not None and self.clock.get_time() >= until:
                break
            if max_events is not None and events_processed >= max_events:
                break
            
            # Check if next event is beyond time limit
            if until is not None and self.queue[0].scheduled_time > until:
                break
            
            if not self.process_next():
                break
            
            events_processed += 1
        
        self.logger.info(f"Simulation completed: {events_processed} events processed, "
                        f"time={self.clock.get_time():.6f}")
    
    def step(self) -> bool:
        """
        Process a single event (step mode for debugging).
        
        Returns:
            True if an event was processed
        """
        return self.process_next()
    
    def clear(self) -> None:
        """Clear all scheduled events."""
        self.queue.clear()
        if self.enable_tracing:
            self.logger.debug("Event queue cleared")
    
    def is_empty(self) -> bool:
        """Check if event queue is empty."""
        return len(self.queue) == 0
    
    def size(self) -> int:
        """Get number of events in queue."""
        return len(self.queue)
    
    def peek_next(self) -> Optional[Event]:
        """
        Peek at the next event without processing it.
        
        Returns:
            Next event or None if queue is empty
        """
        return self.queue[0] if self.queue else None
    
    def get_trace(self) -> List[Event]:
        """
        Get the event trace (if tracing is enabled).
        
        Returns:
            List of processed events
        """
        return self.event_trace.copy()
    
    def reset(self) -> None:
        """Reset the event queue and clock."""
        self.clear()
        self.clock.set_time(0.0)
        self.event_counter = 0
        self.event_trace.clear()
        if self.enable_tracing:
            self.logger.debug("Event queue reset")
