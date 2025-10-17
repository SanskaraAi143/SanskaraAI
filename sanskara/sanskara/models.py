import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Date, DECIMAL, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class Wedding(Base):
    __tablename__ = 'weddings'
    wedding_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wedding_name = Column(String(255), nullable=False)
    wedding_date = Column(Date)
    wedding_location = Column(Text)
    wedding_tradition = Column(Text)
    wedding_style = Column(String(100))
    status = Column(String(50), nullable=False, default='onboarding_in_progress')
    details = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="wedding")
    wedding_members = relationship("WeddingMember", back_populates="wedding")
    workflows = relationship("Workflow", back_populates="wedding")
    tasks = relationship("Task", back_populates="wedding")
    budget_items = relationship("BudgetItem", back_populates="wedding")
    guest_list = relationship("Guest", back_populates="wedding")
    mood_boards = relationship("MoodBoard", back_populates="wedding")
    timeline_events = relationship("TimelineEvent", back_populates="wedding")
    chat_sessions = relationship("ChatSession", back_populates="wedding")
    user_shortlisted_vendors = relationship("UserShortlistedVendor", back_populates="wedding")
    bookings = relationship("Booking", back_populates="wedding")
    image_artifacts = relationship("ImageArtifact", back_populates="wedding")

    def __repr__(self):
        return f"<Wedding(wedding_id='{self.wedding_id}', wedding_name='{self.wedding_name}')>"

class User(Base):
    __tablename__ = 'users'
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supabase_auth_uid = Column(UUID(as_uuid=True), unique=True, nullable=False) # REFERENCES auth.users(id)
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255))
    wedding_id = Column(UUID(as_uuid=True), ForeignKey('weddings.wedding_id', ondelete='SET NULL'))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    preferences = Column(JSONB)
    user_type = Column(String(50), nullable=False, default='customer')

    wedding = relationship("Wedding", back_populates="users")
    wedding_memberships = relationship("WeddingMember", back_populates="user")
    task_feedback = relationship("TaskFeedback", back_populates="user")
    task_approvals = relationship("TaskApproval", back_populates="approved_by_user")
    bookings = relationship("Booking", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    notifications = relationship("Notification", back_populates="recipient_user")

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', email='{self.email}')>"

class WeddingMember(Base):
    __tablename__ = 'wedding_members'
    wedding_id = Column(UUID(as_uuid=True), ForeignKey('weddings.wedding_id', ondelete='CASCADE'), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    role = Column(String(50), nullable=False)

    wedding = relationship("Wedding", back_populates="wedding_members")
    user = relationship("User", back_populates="wedding_memberships")

    def __repr__(self):
        return f"<WeddingMember(wedding_id='{self.wedding_id}', user_id='{self.user_id}', role='{self.role}')>"

class Workflow(Base):
    __tablename__ = 'workflows'
    workflow_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wedding_id = Column(UUID(as_uuid=True), ForeignKey('weddings.wedding_id', ondelete='CASCADE'), nullable=False)
    workflow_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default='not_started')
    context_summary = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    wedding = relationship("Wedding", back_populates="workflows")

    __table_args__ = (UniqueConstraint('wedding_id', 'workflow_name'),)

    def __repr__(self):
        return f"<Workflow(workflow_id='{self.workflow_id}', workflow_name='{self.workflow_name}')>"

class Task(Base):
    __tablename__ = 'tasks'
    task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wedding_id = Column(UUID(as_uuid=True), ForeignKey('weddings.wedding_id', ondelete='CASCADE'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    is_complete = Column(Boolean, default=False)
    due_date = Column(Date)
    priority = Column(String(10), default='medium')
    category = Column(String(100))
    status = Column(String(20), nullable=False, default='No Status')
    lead_party = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    wedding = relationship("Wedding", back_populates="tasks")
    feedback = relationship("TaskFeedback", back_populates="task")
    approvals = relationship("TaskApproval", back_populates="task")

    __table_args__ = (UniqueConstraint('wedding_id', 'title'),)

    def __repr__(self):
        return f"<Task(task_id='{self.task_id}', title='{self.title}')>"

class TaskFeedback(Base):
    __tablename__ = 'task_feedback'
    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('tasks.task_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    feedback_type = Column(String(50), nullable=False)
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())

    task = relationship("Task", back_populates="feedback")
    user = relationship("User", back_populates="task_feedback")

    def __repr__(self):
        return f"<TaskFeedback(feedback_id='{self.feedback_id}', task_id='{self.task_id}', type='{self.feedback_type}')>"

class TaskApproval(Base):
    __tablename__ = 'task_approvals'
    approval_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('tasks.task_id', ondelete='CASCADE'), nullable=False)
    approving_party = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default='pending')
    approved_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    task = relationship("Task", back_populates="approvals")
    approved_by_user = relationship("User", back_populates="task_approvals")

    def __repr__(self):
        return f"<TaskApproval(approval_id='{self.approval_id}', task_id='{self.task_id}', status='{self.status}')>"

class BudgetItem(Base):
    __tablename__ = 'budget_items'
    item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wedding_id = Column(UUID(as_uuid=True), ForeignKey('weddings.wedding_id', ondelete='CASCADE'), nullable=False)
    item_name = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    amount = Column(DECIMAL(12, 2), nullable=False)
    vendor_name = Column(Text)
    status = Column(String(50), default='Pending')
    contribution_by = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    wedding = relationship("Wedding", back_populates="budget_items")

    __table_args__ = (UniqueConstraint('wedding_id', 'item_name', 'category'),)

    def __repr__(self):
        return f"<BudgetItem(item_id='{self.item_id}', item_name='{self.item_name}', amount='{self.amount}')>"

class Guest(Base):
    __tablename__ = 'guest_list'
    guest_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wedding_id = Column(UUID(as_uuid=True), ForeignKey('weddings.wedding_id', ondelete='CASCADE'), nullable=False)
    guest_name = Column(Text, nullable=False)
    contact_info = Column(Text)
    relation = Column(Text)
    side = Column(String(50))
    status = Column(String(50), default='Pending')
    dietary_requirements = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    wedding = relationship("Wedding", back_populates="guest_list")

    def __repr__(self):
        return f"<Guest(guest_id='{self.guest_id}', guest_name='{self.guest_name}')>"

class MoodBoard(Base):
    __tablename__ = 'mood_boards'
    mood_board_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wedding_id = Column(UUID(as_uuid=True), ForeignKey('weddings.wedding_id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False, default='Wedding Mood Board')
    description = Column(Text)
    visibility = Column(String(50), nullable=False, default='shared')
    owner_party = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    wedding = relationship("Wedding", back_populates="mood_boards")
    items = relationship("MoodBoardItem", back_populates="mood_board")

    def __repr__(self):
        return f"<MoodBoard(mood_board_id='{self.mood_board_id}', name='{self.name}')>"

class ImageArtifact(Base):
    __tablename__ = 'image_artifacts'
    artifact_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wedding_id = Column(UUID(as_uuid=True), ForeignKey('weddings.wedding_id', ondelete='CASCADE'), nullable=False)
    artifact_filename = Column(Text, nullable=False)
    supabase_url = Column(Text, nullable=False)
    generation_prompt = Column(Text)
    image_type = Column(String(30), nullable=False, default='generated')
    image_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    wedding = relationship("Wedding", back_populates="image_artifacts")
    mood_board_items = relationship("MoodBoardItem", back_populates="artifact")

    def __repr__(self):
        return f"<ImageArtifact(artifact_id='{self.artifact_id}', filename='{self.artifact_filename}')>"

class MoodBoardItem(Base):
    __tablename__ = 'mood_board_items'
    item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mood_board_id = Column(UUID(as_uuid=True), ForeignKey('mood_boards.mood_board_id', ondelete='CASCADE'), nullable=False)
    image_url = Column(Text, nullable=False)
    note = Column(Text)
    category = Column(String(100), default='Decorations')
    artifact_id = Column(UUID(as_uuid=True), ForeignKey('image_artifacts.artifact_id', ondelete='SET NULL'))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    mood_board = relationship("MoodBoard", back_populates="items")
    artifact = relationship("ImageArtifact", back_populates="mood_board_items")

    def __repr__(self):
        return f"<MoodBoardItem(item_id='{self.item_id}', mood_board_id='{self.mood_board_id}')>"

class TimelineEvent(Base):
    __tablename__ = 'timeline_events'
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wedding_id = Column(UUID(as_uuid=True), ForeignKey('weddings.wedding_id', ondelete='CASCADE'), nullable=False)
    event_name = Column(Text, nullable=False)
    event_date_time = Column(DateTime(timezone=True), nullable=False)
    location = Column(Text)
    description = Column(Text)
    visibility = Column(String(50), nullable=False, default='shared')
    relevant_party = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    wedding = relationship("Wedding", back_populates="timeline_events")

    def __repr__(self):
        return f"<TimelineEvent(event_id='{self.event_id}', event_name='{self.event_name}')>"

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wedding_id = Column(UUID(as_uuid=True), ForeignKey('weddings.wedding_id', ondelete='CASCADE'), nullable=False)
    adk_session_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), default=func.now())
    last_updated_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    summary = Column(JSONB)
    final_summary = Column(Text)

    wedding = relationship("Wedding", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session")

    def __repr__(self):
        return f"<ChatSession(session_id='{self.session_id}', wedding_id='{self.wedding_id}')>"

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_sessions.session_id', ondelete='CASCADE'), nullable=False)
    sender_type = Column(String(20), nullable=False)
    sender_name = Column(String(100), nullable=False)
    content = Column(JSONB, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=func.now())

    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage(message_id='{self.message_id}', session_id='{self.session_id}', sender='{self.sender_name}')>"

class UserShortlistedVendor(Base):
    __tablename__ = 'user_shortlisted_vendors'
    user_vendor_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wedding_id = Column(UUID(as_uuid=True), ForeignKey('weddings.wedding_id', ondelete='CASCADE'), nullable=False)
    vendor_name = Column(Text, nullable=False)
    vendor_category = Column(String(100), nullable=False)
    contact_info = Column(Text)
    status = Column(String(50), nullable=False, default='contacted')
    booked_date = Column(Date)
    notes = Column(Text)
    linked_vendor_id = Column(UUID(as_uuid=True), ForeignKey('vendors.vendor_id'))
    estimated_cost = Column(DECIMAL(12,2))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    wedding = relationship("Wedding", back_populates="user_shortlisted_vendors")
    linked_vendor = relationship("Vendor", back_populates="user_shortlisted_entries")
    bookings = relationship("Booking", back_populates="user_shortlisted_vendor")

    def __repr__(self):
        return f"<UserShortlistedVendor(user_vendor_id='{self.user_vendor_id}', vendor_name='{self.vendor_name}')>"

class Vendor(Base):
    __tablename__ = 'vendors'
    vendor_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_name = Column(String(255), nullable=False)
    vendor_category = Column(String(100), nullable=False)
    contact_email = Column(String(255))
    phone_number = Column(String(50))
    website_url = Column(Text)
    address = Column(JSONB)
    pricing_range = Column(JSONB)
    rating = Column(Float)
    description = Column(Text)
    details = Column(JSONB)
    portfolio_image_urls = Column(ARRAY(Text))
    is_active = Column(Boolean, default=True)
    status = Column(String(50), default='active')
    supabase_auth_uid = Column(UUID(as_uuid=True), unique=True) # REFERENCES auth.users(id)
    is_verified = Column(Boolean, default=False)
    commission_rate = Column(DECIMAL(5,2), default=0.05)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    staff = relationship("VendorStaff", back_populates="vendor")
    services = relationship("VendorService", back_populates="vendor")
    availability = relationship("VendorAvailability", back_populates="vendor")
    bookings = relationship("Booking", back_populates="vendor")
    reviews = relationship("Review", back_populates="vendor")
    vendor_tasks = relationship("VendorTask", back_populates="vendor")
    user_shortlisted_entries = relationship("UserShortlistedVendor", back_populates="linked_vendor")
    staff_portfolios = relationship("StaffPortfolio", back_populates="vendor")
    vendor_service_staff_assignments = relationship("VendorServiceStaff", back_populates="vendor")
    vendor_staff_availability = relationship("VendorStaffAvailability", back_populates="vendor")

    def __repr__(self):
        return f"<Vendor(vendor_id='{self.vendor_id}', vendor_name='{self.vendor_name}', category='{self.vendor_category}')>"

class VendorStaff(Base):
    __tablename__ = 'vendor_staff'
    staff_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey('vendors.vendor_id', ondelete='CASCADE'), nullable=False)
    supabase_auth_uid = Column(UUID(as_uuid=True), unique=True, nullable=False) # REFERENCES auth.users(id)
    email = Column(String(255), unique=True, nullable=False)
    phone_number = Column(String(50))
    display_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default='staff')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    vendor = relationship("Vendor", back_populates="staff")
    responsible_for_services = relationship("VendorService", back_populates="responsible_staff")
    vendor_tasks = relationship("VendorTask", back_populates="assigned_staff")
    notifications = relationship("Notification", back_populates="recipient_staff")
    staff_portfolios = relationship("StaffPortfolio", back_populates="staff")
    vendor_service_staff_assignments = relationship("VendorServiceStaff", back_populates="staff")
    vendor_staff_availability = relationship("VendorStaffAvailability", back_populates="staff")

    def __repr__(self):
        return f"<VendorStaff(staff_id='{self.staff_id}', display_name='{self.display_name}', vendor_id='{self.vendor_id}')>"

class VendorService(Base):
    __tablename__ = 'vendor_services'
    service_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey('vendors.vendor_id', ondelete='CASCADE'), nullable=False)
    service_name = Column(String(255), nullable=False)
    service_category = Column(String(100), nullable=False)
    description = Column(Text)
    base_price = Column(DECIMAL(12, 2))
    price_unit = Column(String(50))
    min_capacity = Column(Integer)
    max_capacity = Column(Integer)
    customizability_details = Column(JSONB)
    is_in_house = Column(Boolean, default=True)
    is_negotiable = Column(Boolean, default=False)
    responsible_staff_id = Column(UUID(as_uuid=True), ForeignKey('vendor_staff.staff_id', ondelete='SET NULL'))
    portfolio_image_urls = Column(ARRAY(Text))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    vendor = relationship("Vendor", back_populates="services")
    responsible_staff = relationship("VendorStaff", back_populates="responsible_for_services")
    booking_services = relationship("BookingService", back_populates="vendor_service")
    vendor_service_staff_assignments = relationship("VendorServiceStaff", back_populates="vendor_service")

    def __repr__(self):
        return f"<VendorService(service_id='{self.service_id}', name='{self.service_name}', vendor_id='{self.vendor_id}')>"

class VendorAvailability(Base):
    __tablename__ = 'vendor_availability'
    availability_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey('vendors.vendor_id', ondelete='CASCADE'), nullable=False)
    available_date = Column(Date, nullable=False)
    status = Column(String(50), nullable=False, default='available')
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    vendor = relationship("Vendor", back_populates="availability")

    __table_args__ = (UniqueConstraint('vendor_id', 'available_date'),)

    def __repr__(self):
        return f"<VendorAvailability(availability_id='{self.availability_id}', vendor_id='{self.vendor_id}', date='{self.available_date}')>"

class Booking(Base):
    __tablename__ = 'bookings'
    booking_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wedding_id = Column(UUID(as_uuid=True), ForeignKey('weddings.wedding_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey('vendors.vendor_id', ondelete='CASCADE'), nullable=False)
    user_shortlisted_vendor_id = Column(UUID(as_uuid=True), ForeignKey('user_shortlisted_vendors.user_vendor_id', ondelete='SET NULL'))
    event_date = Column(Date, nullable=False)
    booking_status = Column(String(50), nullable=False, default='pending_confirmation')
    total_amount = Column(DECIMAL(12, 2))
    advance_amount_due = Column(DECIMAL(12, 2))
    paid_amount = Column(DECIMAL(12, 2), default=0.00)
    commission_rate_applied = Column(DECIMAL(5,4))
    commission_amount = Column(DECIMAL(12,2))
    contract_details_url = Column(Text)
    notes_for_vendor = Column(Text)
    notes_for_user = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    wedding = relationship("Wedding", back_populates="bookings")
    user = relationship("User", back_populates="bookings")
    vendor = relationship("Vendor", back_populates="bookings")
    user_shortlisted_vendor = relationship("UserShortlistedVendor", back_populates="bookings")
    services = relationship("BookingService", back_populates="booking")
    payments = relationship("Payment", back_populates="booking")
    vendor_tasks = relationship("VendorTask", back_populates="booking")
    review = relationship("Review", back_populates="booking", uselist=False)

    def __repr__(self):
        return f"<Booking(booking_id='{self.booking_id}', wedding_id='{self.wedding_id}', vendor_id='{self.vendor_id}')>"

class BookingService(Base):
    __tablename__ = 'booking_services'
    booking_service_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey('bookings.booking_id', ondelete='CASCADE'), nullable=False)
    vendor_service_id = Column(UUID(as_uuid=True), ForeignKey('vendor_services.service_id', ondelete='RESTRICT'), nullable=False)
    negotiated_price = Column(DECIMAL(12,2))
    quantity = Column(Integer, default=1)
    service_specific_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())

    booking = relationship("Booking", back_populates="services")
    vendor_service = relationship("VendorService", back_populates="booking_services")

    def __repr__(self):
        return f"<BookingService(booking_service_id='{self.booking_service_id}', booking_id='{self.booking_id}', vendor_service_id='{self.vendor_service_id}')>"

class Payment(Base):
    __tablename__ = 'payments'
    payment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey('bookings.booking_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False)
    amount = Column(DECIMAL(12, 2), nullable=False)
    payment_method = Column(String(100))
    transaction_id = Column(String(255))
    payment_status = Column(String(50), nullable=False, default='pending')
    payment_type = Column(String(50), nullable=False, default='advance')
    notes = Column(Text)
    paid_at = Column(DateTime(timezone=True), default=func.now())
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    booking = relationship("Booking", back_populates="payments")
    user = relationship("User", back_populates="payments")

    def __repr__(self):
        return f"<Payment(payment_id='{self.payment_id}', booking_id='{self.booking_id}', amount='{self.amount}')>"

class VendorTask(Base):
    __tablename__ = 'vendor_tasks'
    vendor_task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey('bookings.booking_id', ondelete='CASCADE'), nullable=False)
    assigned_staff_id = Column(UUID(as_uuid=True), ForeignKey('vendor_staff.staff_id', ondelete='SET NULL'))
    vendor_id = Column(UUID(as_uuid=True), ForeignKey('vendors.vendor_id', ondelete='CASCADE'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    is_complete = Column(Boolean, default=False)
    due_date = Column(Date)
    priority = Column(String(10), default='medium')
    category = Column(String(100))
    status = Column(String(20), nullable=False, default='To Do')
    dependency_task_id = Column(UUID(as_uuid=True), ForeignKey('vendor_tasks.vendor_task_id'))
    user_facing = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    booking = relationship("Booking", back_populates="vendor_tasks")
    assigned_staff = relationship("VendorStaff", back_populates="vendor_tasks")
    vendor = relationship("Vendor", back_populates="vendor_tasks")
    dependent_tasks = relationship("VendorTask", backref="dependency", remote_side=[vendor_task_id])

    def __repr__(self):
        return f"<VendorTask(vendor_task_id='{self.vendor_task_id}', title='{self.title}', vendor_id='{self.vendor_id}')>"

class Review(Base):
    __tablename__ = 'reviews'
    review_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey('bookings.booking_id', ondelete='CASCADE'), unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey('vendors.vendor_id', ondelete='CASCADE'), nullable=False)
    rating = Column(Float, nullable=False)
    comment = Column(Text)
    review_visibility = Column(String(20), default='public')
    created_at = Column(DateTime(timezone=True), default=func.now())

    booking = relationship("Booking", back_populates="review")
    user = relationship("User", back_populates="reviews")
    vendor = relationship("Vendor", back_populates="reviews")

    def __repr__(self):
        return f"<Review(review_id='{self.review_id}', booking_id='{self.booking_id}', rating='{self.rating}')>"

class Notification(Base):
    __tablename__ = 'notifications'
    notification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'))
    recipient_staff_id = Column(UUID(as_uuid=True), ForeignKey('vendor_staff.staff_id', ondelete='CASCADE'))
    message = Column(Text, nullable=False)
    notification_type = Column(String(100))
    related_entity_type = Column(String(50))
    related_entity_id = Column(UUID(as_uuid=True))
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=func.now())

    recipient_user = relationship("User", back_populates="notifications")
    recipient_staff = relationship("VendorStaff", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(notification_id='{self.notification_id}', type='{self.notification_type}')>"

class TaskTemplate(Base):
    __tablename__ = 'task_templates'
    template_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_name = Column(String(255), unique=True, nullable=False)
    target_actor = Column(String(10), nullable=False)
    trigger_event = Column(String(100))
    tasks = Column(JSONB, nullable=False)

    def __repr__(self):
        return f"<TaskTemplate(template_id='{self.template_id}', name='{self.template_name}')>"

class StaffPortfolio(Base):
    __tablename__ = 'staff_portfolios'
    portfolio_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey('vendor_staff.staff_id', ondelete='CASCADE'), nullable=False)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey('vendors.vendor_id', ondelete='CASCADE'), nullable=False)
    portfolio_type = Column(String(50), nullable=False)
    title = Column(String(255))
    description = Column(Text)
    image_urls = Column(ARRAY(Text))
    video_urls = Column(ARRAY(Text))
    generic_attributes = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    staff = relationship("VendorStaff", back_populates="staff_portfolios")
    vendor = relationship("Vendor", back_populates="staff_portfolios")

    def __repr__(self):
        return f"<StaffPortfolio(portfolio_id='{self.portfolio_id}', staff_id='{self.staff_id}', type='{self.portfolio_type}')>"

class VendorServiceStaff(Base):
    __tablename__ = 'vendor_service_staff'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey('vendors.vendor_id', ondelete='CASCADE'), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey('vendor_services.service_id', ondelete='CASCADE'), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey('vendor_staff.staff_id', ondelete='CASCADE'), nullable=False)
    assigned_role = Column(String(50))
    is_active = Column(Boolean, default=True)
    assigned_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    vendor = relationship("Vendor", back_populates="vendor_service_staff_assignments")
    vendor_service = relationship("VendorService", back_populates="vendor_service_staff_assignments")
    staff = relationship("VendorStaff", back_populates="vendor_service_staff_assignments")

    __table_args__ = (UniqueConstraint('service_id', 'staff_id'),)

    def __repr__(self):
        return f"<VendorServiceStaff(id='{self.id}', service_id='{self.service_id}', staff_id='{self.staff_id}')>"

class VendorStaffAvailability(Base):
    __tablename__ = 'vendor_staff_availability'
    staff_availability_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey('vendor_staff.staff_id', ondelete='CASCADE'), nullable=False)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey('vendors.vendor_id', ondelete='CASCADE'), nullable=False)
    available_date = Column(Date, nullable=False)
    status = Column(String(50), nullable=False, default='available')
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    staff = relationship("VendorStaff", back_populates="vendor_staff_availability")
    vendor = relationship("Vendor", back_populates="vendor_staff_availability")

    __table_args__ = (UniqueConstraint('staff_id', 'available_date'),)

    def __repr__(self):
        return f"<VendorStaffAvailability(staff_availability_id='{self.staff_availability_id}', staff_id='{self.staff_id}', date='{self.available_date}')>"

class Memory(Base):
    __tablename__ = 'memories'
    memory_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_name = Column(Text, nullable=False)
    user_id = Column(Text, nullable=False) # Maps to wedding_id for grouping
    content = Column(JSONB, nullable=False)
    embedding = Column(ARRAY(Float), nullable=False) # This should ideally be vector(1024) but ARRAY(Float) is a generic substitute for SQLAlchemy's lack of direct vector type
    created_at = Column(DateTime(timezone=True), default=func.now())

    def __repr__(self):
        return f"<Memory(memory_id='{self.memory_id}', app_name='{self.app_name}', user_id='{self.user_id}')>"