#include <nanobind/nanobind.h>

namespace nb = nanobind;

struct Animal {
    nb::callable f;

    void call_f() {
        f();
    }
};

NB_MODULE(tulipy, m) {
    nb::class_<Animal>(m, "Animal")
        .def(nb::init<>())
        .def("call_f", &Animal::call_f)
        .def_rw("f", &Animal::f);
}