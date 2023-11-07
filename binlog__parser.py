import re
from datetime import datetime

from decimal import Decimal, InvalidOperation


class Transaction(object):
    def __init__(self, start_date=None, end_date=None, identifiers=None, statements=None):
        self.start_date = start_date
        self.end_date = end_date
        self.identifiers = identifiers or set()
        self.statements = statements or []

    @property
    def duration(self):
        return (self.end_date - self.start_date).seconds if self.end_date and self.start_date else 0

    @property
    def total_changes(self):
        return sum([len(statement.changes) for statement in self.statements])


class BinlogParser(object):
    def __init__(self, column_mapping=None):
        self.column_mapping = column_mapping or {}

    def parse(self, binlog_file): #fetching sql syntax functions from binlog  
        transactions = []
        change_buffer = ''
        last_line = None
        for line in binlog_file:
            if line.startswith("BEGIN"):
                transaction = Transaction()
            elif "Table_map:" in line:
                statement = Statement()
                if not transaction.start_date:
                    transaction.start_date = datetime.strptime(line[1:16], '%y%m%d %H:%M:%S')
                transaction.statements.append(statement)
            elif line.startswith("### UPDATE") or line.startswith("### INSERT") or line.startswith("### DELETE"):
                if change_buffer:
                    statement.changes.append(self._create_change(change_buffer))
                change_buffer = line[4:]
            elif line.startswith("###"):
                change_buffer += line[4:]
            elif line.startswith("# at") and change_buffer:
                statement.changes.append(self._create_change(change_buffer))
                change_buffer = ''
            elif line.startswith("COMMIT"):
                transaction.end_date = datetime.strptime(last_line[1:16], '%y%m%d %H:%M:%S')
                transactions.append(transaction)
            last_line = line
        return transactions
    def _create_change(self, change_buffer): #ignore specified special characters from binlog
        command_type = change_buffer.split(' ')[0]
        change_without_comments = re.sub("/\*.*\*/", "", change_buffer)
        table = self._extract_table(change_without_comments)
        table_name_without_namespace = table.replace('`', '').split('.')[-1]
        column_mapping_for_this_table = self.column_mapping.get(table_name_without_namespace, {})

        def get_actual_name(match): 
            actual_name = column_mapping_for_this_table.get(int(match.group(1)), match.group(0))
            return actual_name if actual_name.startswith('@') else '`{}`'.format(actual_name)
        change_without_comments_and_actual_column_names = re.sub("@(\d+)",
                                                             get_actual_name,
                                                             change_without_comments)

        where_parameters, set_parameters = self._extract_parameter(
            command_type,
            change_without_comments,
            column_mapping_for_this_table
        )

        return Change(
            command_type,
            table,
            change_without_comments_and_actual_column_names if self.column_mapping else change_without_comments,
            where_parameters,
            set_parameters
        )

    def _extract_table(self, change_instruction_without_comments): #change_instruction_without_comments is the syntax embedded in the queries wihtout spl characters
        table_name = re.findall("`.*?`\s", change_instruction_without_comments)[0]#takes the first word (delete/insert/commit)
        return table_name.strip()
