#include <boost/python.hpp>
using namespace boost::python;

namespace { void wrap_foo() {
  class_<MyClass>("MyClass", no_init)
    .def("method_a", &MyClass::method_a, "Does A")
    .def("method_b", &MyClass::method_b)
    .add_property("my_prop", &MyClass::get_prop, &MyClass::set_prop)
    .def_readwrite("verbose", &MyClass::verbose)
  ;
  def("free_func", &free_func_impl);
} }

BOOST_PYTHON_MODULE(my_cpp_ext) {
  wrap_foo();
}
