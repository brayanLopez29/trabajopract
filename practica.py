

from abc import ABC, abstractmethod
from datetime import datetime
import logging



logging.basicConfig(
    filename="software_fj.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)




class SoftwareFJError(Exception):
    pass


class ValidationError(SoftwareFJError):
    pass


class DuplicateError(SoftwareFJError):
    pass


class NotFoundError(SoftwareFJError):
    pass


class ServiceUnavailableError(SoftwareFJError):
    pass


class ReservationError(SoftwareFJError):
    pass


# VALIDATION FUNCTIONS 

def text_required(value, field, minimum=1):
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise ValidationError(f"{field} is required.")
    return value.strip()


def positive_number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValidationError(f"{field} must be a positive number.")
    return value


def valid_email(value):
    value = text_required(value, "Email", 5)
    if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
        raise ValidationError("Invalid email address.")
    return value


def valid_phone(value):
    value = str(value).strip()
    if not value.isdigit() or not 7 <= len(value) <= 15:
        raise ValidationError("Phone must contain 7 to 15 digits.")
    return value




class Entity(ABC):
    def __init__(self, entity_id):
        self._entity_id = text_required(str(entity_id), "ID")

    @property
    def entity_id(self):
        return self._entity_id

    @abstractmethod
    def describe(self):
        pass


#  CLIENT

class client(Entity):
    def __init__(self, client_id, name, email, phone):
        super().__init__(client_id)
        self.__name = text_required(name, "Name", 3)
        self.__email = valid_email(email)
        self.__phone = valid_phone(phone)

    @property
    def name(self):
        return self.__name

    @property
    def email(self):
        return self.__email

    @property
    def phone(self):
        return self.__phone

    def describe(self):
        return f"{self.entity_id} | {self.__name} | {self.__email} | {self.__phone}"




class Service(ABC):
    def __init__(self, service_id, name, base_price):
        self._service_id = text_required(str(service_id), "Service ID")
        self._name = text_required(name, "Service name", 3)
        self._base_price = float(positive_number(base_price, "Base price"))
        self._available = True

    
    @property
    def service_id(self):
        return self._service_id

    @property
    def name(self):
        return self._name

    @property
    def available(self):
        return self._available

    def set_availability(self, status):
        if not isinstance(status, bool):
            raise ValidationError("Availability must be True or False.")
        self._available = status
        logging.info("Service %s availability=%s", self._service_id, status)

    def calculate_cost(self, *args):
        """
        Emulated method overloading:
        calculate_cost(duration)
        calculate_cost(duration, tax_rate)
        calculate_cost(duration, tax_rate, discount)
        """
        if len(args) == 1:
            duration, tax, discount = args[0], 0, 0
        elif len(args) == 2:
            duration, tax = args
            discount = 0
        elif len(args) == 3:
            duration, tax, discount = args
        else:
            raise TypeError("Use duration, optional tax_rate and optional discount.")

        self.validate_parameters(duration)

        if not isinstance(tax, (int, float)) or not 0 <= tax <= 100:
            raise ValidationError("Tax must be between 0 and 100.")

        if not isinstance(discount, (int, float)) or not 0 <= discount <= 100:
            raise ValidationError("Discount must be between 0 and 100.")

        subtotal = self._base_price * duration
        return round(subtotal * (1 - discount / 100) * (1 + tax / 100), 2)

    @abstractmethod
    def validate_parameters(self, duration):
        pass

    @abstractmethod
    def describe(self):
        pass




class RoomReservation(Service):
    def validate_parameters(self, duration):
        positive_number(duration, "Room hours")

    def describe(self):
        return f"Room reservation: {self.name} | Price/hour: ${self._base_price:.2f}"


class EquipmentRental(Service):
    
    def validate_parameters(self, duration):
        if isinstance(duration, bool) or not isinstance(duration, int):
            raise ValidationError("Equipment rental duration must be whole days.")
        positive_number(duration, "Rental days")

    def describe(self):
        return f"Equipment rental: {self.name} | Price/day: ${self._base_price:.2f}"


class SpecializedConsulting(Service):
    def validate_parameters(self, duration):
        positive_number(duration, "Consulting hours")

    def describe(self):
        return f"Specialized consulting: {self.name} | Price/hour: ${self._base_price:.2f}"



class Reservation(Entity):
    def __init__(self, reservation_id, client, service, duration):
        super().__init__(reservation_id)

        if not isinstance(client, Client):
            raise ValidationError("A valid client is required.")

        if not isinstance(service, Service):
            raise ValidationError("A valid service is required.")

        service.validate_parameters(duration)

        self._client = client
        self._service = service
        self._duration = duration
        self._status = "Pending"
        self._total = None
        self._created_at = datetime.now()

    @property
    def client(self):
        return self._client

    @property
    def service(self):
        return self._service

    @property
    def status(self):
        return self._status

    def confirm(self, tax=0, discount=0):
        if self._status != "Pending":
            raise ReservationError("Only pending reservations can be confirmed.")

        if not self._service.available:
            raise ServiceUnavailableError("Selected service is unavailable.")

        try:
            total = self._service.calculate_cost(self._duration, tax, discount)
        except (ValidationError, TypeError, ValueError) as error:
            raise ReservationError("Reservation cost calculation failed.") from error

        if total < 0:
            raise ReservationError("Calculated total cannot be negative.")

        self._total = total
        self._status = "Confirmed"
        logging.info("Reservation %s confirmed: %.2f", self.entity_id, total)
        return total

    def cancel(self):
        if self._status not in ("Pending", "Confirmed"):
            raise ReservationError("This reservation cannot be cancelled.")

        self._status = "Cancelled"
        logging.info("Reservation %s cancelled.", self.entity_id)

    def process(self):
        if self._status != "Confirmed":
            raise ReservationError("Only confirmed reservations can be processed.")

        self._status = "Processed"
        logging.info("Reservation %s processed.", self.entity_id)

    def describe(self):
        total = f"${self._total:.2f}" if self._total is not None else "Not calculated"

        return (
            f"{self.entity_id} | Client: {self._client.name} | "
            f"Service: {self._service.name} | Duration: {self._duration} | "
            f"Status: {self._status} | Total: {total}"
        )





class SoftwareFJ:
    def __init__(self):
        self._clients = []
        self._services = []
        self._reservations = []
        

    @property
    def clients(self):
        return tuple(self._clients)

    
    @property
    def services(self):
        return tuple(self._services)

    @property
    def reservations(self):
        return tuple(self._reservations)

    @staticmethod
    def _unique(collection, identifier, label):
        if any(item.entity_id == identifier for item in collection):
            raise DuplicateError(f"{label} ID {identifier} already exists.")

    def register_client(self, client):
        if not isinstance(client, Client):
            raise ValidationError("Invalid client object.")

        self._unique(self._clients, client.entity_id, "Client")
        self._clients.append(client)
        logging.info("Client registered: %s", client.entity_id)

    def register_service(self, service):
        if not isinstance(service, Service):
            raise ValidationError("Invalid service object.")

        if any(s.service_id == service.service_id for s in self._services):
            raise DuplicateError(f"Service ID {service.service_id} already exists.")

        self._services.append(service)
        logging.info("Service registered: %s", service.service_id)

    def create_reservation(self, reservation):
        if not isinstance(reservation, Reservation):
            raise ValidationError("Invalid reservation object.")

        self._unique(self._reservations, reservation.entity_id, "Reservation")

        if reservation.client not in self._clients:
            raise NotFoundError("Client is not registered.")

        if reservation.service not in self._services:
            raise NotFoundError("Service is not registered.")

        self._reservations.append(reservation)
        logging.info("Reservation created: %s", reservation.entity_id)

    def find_client(self, identifier):
        for client in self._clients:
            if client.entity_id == identifier:
                return client

        raise NotFoundError(f"Client {identifier} was not found.")

    def find_service(self, identifier):
        for service in self._services:
            if service.service_id == identifier:
                return service

        raise NotFoundError(f"Service {identifier} was not found.")

    def find_reservation(self, identifier):
        for reservation in self._reservations:
            if reservation.entity_id == identifier:
                return reservation

        raise NotFoundError(f"Reservation {identifier} was not found.")

    def show_clients(self):
        print("\n--- CLIENTS ---")

        for item in self._clients:
            print(item.describe())

        if not self._clients:
            print("No clients registered.")

    def show_services(self):
        print("\n--- SERVICES ---")

        for item in self._services:
            print(f"{item.service_id} | {item.describe()} | Available: {item.available}")

        if not self._services:
            print("No services registered.")

    def show_reservations(self):
        print("\n--- RESERVATIONS ---")

        for item in self._reservations:
            print(item.describe())

        if not self._reservations:
            print("No reservations registered.")




def ask_text(prompt):
    value = input(prompt).strip()

    if not value:
        raise ValidationError("This field cannot be empty.")

    return value


def ask_float(prompt):
    try:
        return float(input(prompt).strip())

    except ValueError as error:
        raise ValidationError("Enter a valid number.") from error




def menu_register_client(system):
    client = Client(
        ask_text("Client ID: "),
        ask_text("Full name: "),
        ask_text("Email: "),
        ask_text("Phone (digits only): ")
    )

    system.register_client(client)
    print("Client registered successfully.")


def menu_register_service(system):
    print("1. Room reservation")
    print("2. Equipment rental")
    print("3. Specialized consulting")

    option = ask_text("Service type: ")
    sid = ask_text("Service ID: ")
    name = ask_text("Service name: ")
    price = ask_float("Base price: ")

    service_types = {
        "1": RoomReservation,
        "2": EquipmentRental,
        "3": SpecializedConsulting
    }

    if option not in service_types:
        raise ValidationError("Invalid service type.")

    system.register_service(service_types[option](sid, name, price))
    print("Service registered successfully.")


def menu_create_reservation(system):
    rid = ask_text("Reservation ID: ")
    client = system.find_client(ask_text("Client ID: "))
    service = system.find_service(ask_text("Service ID: "))
    duration = ask_float("Duration (hours or days): ")

    if isinstance(service, EquipmentRental):
        if not duration.is_integer():
            raise ValidationError("Equipment rental requires whole days.")

        duration = int(duration)

    reservation = Reservation(rid, client, service, duration)
    system.create_reservation(reservation)

    print("Reservation created with Pending status.")


def menu_confirm_reservation(system):
    reservation = system.find_reservation(ask_text("Reservation ID: "))
    tax = ask_float("Tax percentage (0-100): ")
    discount = ask_float("Discount percentage (0-100): ")

    print(
        f"Reservation confirmed. Total: "
        f"${reservation.confirm(tax, discount):.2f}"
    )


def menu_change_availability(system):
    service = system.find_service(ask_text("Service ID: "))
    answer = ask_text("Set available? (y/n): ").lower()

    if answer not in ("y", "n"):
        raise ValidationError("Enter y or n.")

    service.set_availability(answer == "y")
    print("Availability updated.")


def interactive_menu():
    system = SoftwareFJ()

    actions = {
        "1": lambda: menu_register_client(system),
        "2": lambda: menu_register_service(system),
        "3": lambda: menu_create_reservation(system),
        "4": lambda: menu_confirm_reservation(system),
        "5": lambda: system.find_reservation(ask_text("Reservation ID: ")).cancel(),
        "6": lambda: system.find_reservation(ask_text("Reservation ID: ")).process(),
        "7": lambda: menu_change_availability(system),
        "8": system.show_clients,
        "9": system.show_services,
        "10": system.show_reservations
    }

    while True:
        print("\n========== SOFTWARE FJ ==========")
        print("1. Register client")
        print("2. Register service")
        print("3. Create reservation")
        print("4. Confirm reservation")
        print("5. Cancel reservation")
        print("6. Process reservation")
        print("7. Change service availability")
        print("8. List clients")
        print("9. List services")
        print("10. List reservations")
        print("0. Exit")

        try:
            option = input("Choose an option: ").strip()

            if option == "0":
                print("Goodbye.")
                logging.info("Application closed normally.")
                break

            action = actions.get(option)

            if action is None:
                raise ValidationError("Invalid menu option.")

            action()

        except SoftwareFJError as error:
            logging.exception("Handled application error: %s", error)
            print("Operation failed:", error)

        except (ValueError, TypeError) as error:
            logging.exception("Input/type error: %s", error)
            print("Invalid input:", error)

        except Exception as error:
            logging.exception("Unexpected error: %s", error)
            print("Unexpected error. The application will continue.")

        else:
            logging.info("Menu option %s completed successfully.", option)

        finally:
            print("Operation finished.")


#  AUTOMATIC TESTS: 14 OPERATIONS

def run_demonstration():
    system = SoftwareFJ()

    print("\n--- AUTOMATIC DEMONSTRATION: 14 OPERATIONS ---")

    def test(number, title, operation):
        print(f"\n{number}. {title}")

        try:
            operation()

        except Exception as error:
            logging.exception("Demonstration test %s failed.", number)
            print("Handled error:", error)

        else:
            print("Completed successfully.")

        finally:
            print("Test finished.")

    def t1():
        system.register_client(
            Client("C001", "Carlos Perez", "carlos@example.com", "3001234567")
        )

    def t2():
        system.register_client(
            Client("C002", "Maria Gomez", "maria@example.com", "3101234567")
        )

    def t3():
        Client("C003", "AB", "bad-email", "123")

    def t4():
        system.register_service(
            RoomReservation("S001", "Meeting Room", 50000)
        )

    def t5():
        system.register_service(
            EquipmentRental("S002", "Projector", 30000)
        )

    def t6():
        system.register_service(
            SpecializedConsulting("S003", "Technical Consulting", 80000)
        )

    def t7():
        RoomReservation("S004", "Invalid Room", -100)

    def t8():
        reservation = Reservation(
            "R001",
            system.find_client("C001"),
            system.find_service("S001"),
            2
        )

        system.create_reservation(reservation)
        print(f"Total: ${reservation.confirm(19, 10):.2f}")

    def t9():
        Reservation(
            "R002",
            system.find_client("C002"),
            system.find_service("S002"),
            1.5
        )

    def t10():
        service = system.find_service("S003")
        service.set_availability(False)

        reservation = Reservation(
            "R003",
            system.find_client("C001"),
            service,
            2
        )

        system.create_reservation(reservation)
        reservation.confirm()

    def t11():
        system.find_reservation("R001").cancel()

    def t12():
        system.find_reservation("R001").process()

    def t13():
        system.find_client("C999")

    def t14():
        try:
            raise ValueError("Invalid external input.")

        except ValueError as original:
            raise ValidationError(
                "Input could not be processed."
            ) from original
            

    tests = [
        ("Register valid client", t1),
        ("Register second valid client", t2),
        ("Reject invalid client", t3),
        ("Register room service", t4),
        ("Register equipment service", t5),
        ("Register consulting service", t6),
        ("Reject service with negative price", t7),
        ("Create and confirm reservation", t8),
        ("Reject invalid equipment duration", t9),
        ("Reject unavailable service reservation", t10),
        ("Cancel confirmed reservation", t11),
        ("Reject processing cancelled reservation", t12),
        ("Handle nonexistent client search", t13),
        ("Demonstrate exception chaining", t14)
    ]

    for number, (title, operation) in enumerate(tests, start=1):
        test(number, title, operation)

    system.show_clients()
    system.show_services()
    system.show_reservations()

    print("\nAll 14 operations were attempted. Check software_fj.log.")

    return system


# MAIN PROGRAM 

if __name__ == "__main__":
    print("SOFTWARE FJ - INTEGRATED MANAGEMENT SYSTEM")
    print("1. Interactive management menu")
    print("2. Automatic demonstration (14 operations)")

    try:
        choice = input("Choose 1 or 2: ").strip()

        if choice == "1":
            interactive_menu()

        elif choice == "2":
            run_demonstration()

        else:
            raise ValidationError("Choose option 1 or 2.")

    except SoftwareFJError as error:
        logging.exception("Startup error: %s", error)
        print("Application error:", error)

    except Exception as error:
        logging.exception("Critical startup error: %s", error)
        print("Unexpected error:", error)

    else:
        logging.info("Main execution completed.")

    finally:
        print("\nSoftware FJ program finished.")


        
