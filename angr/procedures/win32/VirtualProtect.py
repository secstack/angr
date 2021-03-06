import angr
import logging

from .VirtualAlloc import convert_prot, deconvert_prot

l = logging.getLogger('angr.procedures.win32.VirtualProtect')

class VirtualProtect(angr.SimProcedure):
    def run(self, lpAddress, dwSize, flNewProtect, lpfOldProtect):
        addrs = self.state.se.any_n_int(lpAddress, 2)
        if len(addrs) != 1:
            raise angr.errors.SimValueError("VirtualProtect can't handle symbolic lpAddress")
        addr = addrs[0]

        size = self.state.se.max_int(dwSize)
        if dwSize.symbolic and size > self.state.libc.max_variable_size:
            l.warning('symbolic VirtuaProtect dwSize %s has maximum %#x, greater than state.libc.max_variable_size %#x',
                      dwSize, size, self.state.libc.max_variable_size)
            size = self.state.libc.max_variable_size

        prots = self.state.se.any_n_int(flNewProtect, 2)
        if len(prots) != 1:
            raise angr.errors.SimValueError("VirtualProtect can't handle symbolic flNewProtect")
        prot = prots[0]
        angr_prot = convert_prot(prot)

        try:
            if not self.state.solver.is_false(self.state.memory.permissions(lpfOldProtect) & 2 == 0):
                return 0
        except angr.errors.SimMemoryError:
            return 0

        page_start = addr & ~0xfff
        page_end = (addr + size - 1) & ~0xfff
        first_prot = None
        try:
            for page in range(page_start, page_end + 0x1000, 0x1000):
                old_prot = self.state.memory.permissions(page)
                if first_prot is None:
                    first_prot = self.state.solver.any_int(old_prot)
        except angr.errors.SimMemoryError:
            return 0

        # we're good! make the changes.
        for page in range(page_start, page_end + 0x1000, 0x1000):
            self.state.memory.permissions(page, angr_prot)

        self.state.mem[lpfOldProtect].dword = deconvert_prot(first_prot)
        return 1
