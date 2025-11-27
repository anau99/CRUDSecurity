# CRUD Desktop Application with Security and OOP

import json
import os
import jwt
import datetime

SECRET_KEY = "your-secret-key"  # Will be used to sign JWT tokens

class User:
    """Base class for users with different roles"""
    
    def __init__(self, username, password, role):
        self.username = username
        self.password = password
        self.role = role
        
    def __repr__(self):
        return f"User(username='{self.username}', role='{self.role}')"


class Admin(User):
    """Class representing an Admin user"""
    
    def __init__(self, username, password):
        super().__init__(username, password, role='admin')


class Employee:
    """Class representing an employee record"""
    
    def __init__(self, id, name, position, department):
        self.id = id
        self.name = name
        self.position = position
        self.department = department
        self.status = 'pending'  # New attribute: approval status
        self.manager_approver = None
        self.admin_approver = None
        
    def to_dict(self):
        """Convert employee object to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'position': self.position,
            'department': self.department,
            'status': self.status,
            'manager_approver': self.manager_approver,
            'admin_approver': self.admin_approver
        }
        
    @staticmethod
    def from_dict(data):
        """Create Employee object from dictionary"""
        emp = Employee(
            id=data['id'],
            name=data['name'],
            position=data['position'],
            department=data['department']
        )
        emp.status = data.get('status', 'pending')
        emp.manager_approver = data.get('manager_approver')
        emp.admin_approver = data.get('admin_approver')
        return emp
        

class SecurityController:
    """Handles authentication and authorization"""
    
    def __init__(self):
        self.current_user = None
        self.employees = self.load_employees()
        
    def load_users(self):
        """Load users from JSON file"""
        if not os.path.exists('data/users.json'):
            # Create default users if file doesn't exist
            default_users = {
                'users': [
                    {'username': 'admin', 'password': 'admin123', 'role': 'admin'},
                    {'username': 'employee', 'password': 'employee123', 'role': 'employee'},
                    {'username': 'manager', 'password': 'manager123', 'role': 'manager'}
                ]
            }
            os.makedirs('data', exist_ok=True)
            with open('data/users.json', 'w') as f:
                json.dump(default_users, f, indent=4)
            return default_users['users']
        
        with open('data/users.json', 'r') as f:
            data = json.load(f)
        return data['users']
    
    def authenticate(self, username, password):
        """Authenticate user and set current user"""
        users = self.load_users()
        for user_data in users:
            if user_data['username'] == username and user_data['password'] == password:
                if user_data['role'] == 'admin':
                    self.current_user = Admin(username=username, password=password)
                else:
                    self.current_user = User(
                        username=username,
                        password=password,
                        role=user_data['role']
                    )
                
                # Generate JWT token
                payload = {
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1),
                    'username': username,
                    'role': user_data['role']
                }
                token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
                print(f"JWT Token: {token}")
                return True
        return False
    
    def has_permission(self, action, target_employee=None):
        """Check if current user has permission for the action"""
        if not self.current_user:
            return False
            
        role = self.current_user.role
        if action == 'create':
            return role == 'admin'
        elif action == 'read':
            return role in ['admin', 'employee', 'manager']
        elif action == 'update':
            if role == 'admin':
                return True
            if role == 'employee' and target_employee:
                return target_employee.id == self.current_user.username  # Assuming employee ID matches username
            return False
        elif action == 'delete':
            return role == 'admin'
        return False
        
    def load_employees(self):
        """Load employees from JSON file"""
        if not os.path.exists('data/employees.json'):
            os.makedirs('data', exist_ok=True)
            with open('data/employees.json', 'w') as f:
                json.dump({'employees': []}, f, indent=4)
            return []
            
        with open('data/employees.json', 'r') as f:
            data = json.load(f)
        return [Employee.from_dict(emp) for emp in data['employees']]
    
    def save_employees(self):
        """Save employees to JSON file"""
        data = {'employees': [emp.to_dict() for emp in self.employees]}
        with open('data/employees.json', 'w') as f:
            json.dump(data, f, indent=4)
            
    # CRUD operations with permission checks
    def create_employee(self, name, position, department):
        """Create a new employee record"""
        if not self.has_permission('create'):
            raise PermissionError("You do not have permission to create employees")
            
        # Generate new ID
        new_id = str(len(self.employees) + 1)
        new_employee = Employee(new_id, name, position, department)
        self.employees.append(new_employee)
        self.save_employees()
        return new_employee
        
    def read_employees(self):
        """Read all employees"""
        if not self.has_permission('read'):
            raise PermissionError("You do not have permission to read employees")
            
        return self.employees
        
    def read_employee(self, employee_id):
        """Read a specific employee"""
        if not self.has_permission('read'):
            raise PermissionError("You do not have permission to read employees")
            
        for emp in self.employees:
            if emp.id == employee_id:
                return emp
        return None
        
    def update_employee(self, employee_id, name=None, position=None, department=None):
        """Update an existing employee record"""
        if not self.has_permission('update'):
            raise PermissionError("You do not have permission to update employees")
            
        employee = self.read_employee(employee_id)
        if not employee:
            raise ValueError("Employee not found")
            
        # For employee role, only allow self update
        if self.current_user.role == 'employee' and employee_id != self.current_user.username:
            raise PermissionError("Employees can only update their own records")
            
        if name is not None:
            employee.name = name
        if position is not None:
            employee.position = position
        if department is not None:
            employee.department = department
            
        self.save_employees()
        return employee
        
    def delete_employee(self, employee_id):
        """Delete an employee record"""
        if not self.has_permission('delete'):
            raise PermissionError("You do not have permission to delete employees")
            
        employee = self.read_employee(employee_id)
        if not employee:
            raise ValueError("Employee not found")
            
        self.employees.remove(employee)
        self.save_employees()
        return True
        
    def approve_employee_by_manager(self, employee_id):
        """Manager approves an employee"""
        if not self.current_user or self.current_user.role != 'manager':
            raise PermissionError("Only managers can approve employees")
            
        employee = self.read_employee(employee_id)
        if not employee:
            raise ValueError("Employee not found")
            
        if employee.status != 'pending':
            raise ValueError("Employee is not pending approval")
            
        employee.status = 'manager_approved'
        employee.manager_approver = self.current_user.username
        self.save_employees()
        return employee
        
    def approve_employee_by_admin(self, employee_id):
        """Admin gives final approval to an employee"""
        if not self.current_user or self.current_user.role != 'admin':
            raise PermissionError("Only admins can give final approval")
            
        employee = self.read_employee(employee_id)
        if not employee:
            raise ValueError("Employee not found")
            
        if employee.status != 'manager_approved':
            raise ValueError("Employee needs manager approval first")
            
        employee.status = 'approved'
        employee.admin_approver = self.current_user.username
        self.save_employees()
        return employee


# Example usage
if __name__ == "__main__":
    controller = SecurityController()
    if controller.authenticate('admin', 'admin123'):
        controller.create_employee("Paul Mccartney","DE","IT")
    
    print("=== Testing Employee Approval Process ===")
    
    # Step 1: Create a new employee (should be in 'pending' state)
    if controller.authenticate('admin', 'admin123'):
        print("Authenticated as admin")
        try:
            new_emp = controller.create_employee("John Doe", "Developer", "IT")
            print(f"Created employee: {new_emp.name} (ID: {new_emp.id}, Status: {new_emp.status})")
        except Exception as e:
            print(f"Error creating employee: {str(e)}")
        controller.current_user = None  # Logout admin
    else:
        print("Admin authentication failed")
        
    # Step 2: Manager approves the employee
    if controller.authenticate('manager', 'manager123'):
        print("Authenticated as manager")
        try:
            # Find the pending employee
            employees = controller.read_employees()
            pending_emp = next((e for e in employees if e.status == 'pending'), None)
            
            if pending_emp:
                approved_emp = controller.approve_employee_by_manager(pending_emp.id)
                print(f"Manager approved employee: {approved_emp.name} (ID: {approved_emp.id}, Status: {approved_emp.status})")
            else:
                print("No pending employees found for approval")
        except Exception as e:
            print(f"Error in manager approval: {str(e)}")
        controller.current_user = None  # Logout manager
    else:
        print("Manager authentication failed")
        
    # Step 3: Admin gives final approval
    if controller.authenticate('admin', 'admin123'):
        print("Authenticated as admin for final approval")
        try:
            # Find the manager-approved employee
            employees = controller.read_employees()
            manager_approved_emp = next((e for e in employees if e.status == 'manager_approved'), None)
            
            if manager_approved_emp:
                final_approved_emp = controller.approve_employee_by_admin(manager_approved_emp.id)
                print(f"Admin final approved employee: {final_approved_emp.name} (ID: {final_approved_emp.id}, Status: {final_approved_emp.status})")
            else:
                print("No manager-approved employees found for final approval")
        except Exception as e:
            print(f"Error in admin final approval: {str(e)}")
    else:
        print("Admin authentication failed for final approval")
